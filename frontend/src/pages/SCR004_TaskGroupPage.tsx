/**
 * タスクグループ管理ページ（SCR004）。
 * タスクグループ一覧・進捗サマリー・グループ名編集・削除を提供する。
 * グループの新規作成・チケットの追加はチケット一覧画面（SCR001）から行う。
 */
import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import GroupWorkIcon from '@mui/icons-material/GroupWork'
import { taskGroupsApi } from '../api/endpoints/apis'
import type { TaskGroupItem, TaskGroupUpdateRequest } from '../api/endpoints/types'

/** ページ内 query key（定数化でタイポ防止） */
const QUERY_KEY = ['task-groups'] as const

/**
 * 完了扱いとするステータス。
 * co-change: SCR001_TicketListPage.tsx CLOSED_STATUSES / app/features/tickets の closed ステータス定数
 */
const CLOSED_STATUSES = new Set(['resolved', 'closed', 'rejected'])

/** グループ全体の進捗率（完了件数/全件数）を 0-100 で返す */
function calcProgress(members: TaskGroupItem['members']): number {
  if (members.length === 0) return 0
  const done = members.filter((m) => CLOSED_STATUSES.has(m.status)).length
  return Math.round((done / members.length) * 100)
}

// ---- ステータス表示定数 -------------------------------------------------------

const STATUS_COLOR: Record<string, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
  new: 'info',
  in_progress: 'warning',
  resolved: 'success',
  closed: 'default',
  rejected: 'error',
}

const STATUS_LABEL: Record<string, string> = {
  new: '新規',
  in_progress: '進行中',
  resolved: '解決済み',
  closed: '終了',
  rejected: '却下',
}

// ---- グループ名編集ダイアログ -----------------------------------------------

interface EditGroupDialogProps {
  group: TaskGroupItem | null
  onClose: () => void
}

/**
 * タスクグループのグループ名・説明を編集するダイアログ。
 * 保存成功時にグループ一覧クエリを無効化して自動リフレッシュする。
 */
function EditGroupDialog({ group, onClose }: EditGroupDialogProps) {
  const open = group !== null
  const [name, setName] = useState(group?.name ?? '')
  const [description, setDescription] = useState(group?.description ?? '')

  React.useEffect(() => {
    if (group) {
      setName(group.name)
      setDescription(group.description ?? '')
    }
  }, [group?.id])

  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (data: TaskGroupUpdateRequest) =>
      taskGroupsApi.update(group!.id, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      onClose()
    },
  })

  const handleClose = () => {
    mutation.reset()
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>グループ名を編集</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {mutation.isError && (
            <Alert severity="error">更新に失敗しました。再度お試しください。</Alert>
          )}
          <TextField
            label="グループ名"
            required
            fullWidth
            size="small"
            value={name}
            onChange={(e) => setName(e.target.value)}
            slotProps={{ htmlInput: { maxLength: 200 } }}
            autoFocus
          />
          <TextField
            label="説明（任意）"
            fullWidth
            size="small"
            multiline
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            slotProps={{ htmlInput: { maxLength: 1000 } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate({ name: name.trim(), description: description.trim() || null })}
          disabled={!name.trim() || mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ---- 削除確認ダイアログ -----------------------------------------------------

interface DeleteGroupDialogProps {
  group: TaskGroupItem | null
  onClose: () => void
}

/**
 * タスクグループを削除する確認ダイアログ。
 * グループ論理削除のみ実行。チケット自体は削除しない。
 * 削除成功時にグループ一覧クエリを無効化して自動リフレッシュする。
 */
function DeleteGroupDialog({ group, onClose }: DeleteGroupDialogProps) {
  const open = group !== null
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: () => taskGroupsApi.delete(group!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      onClose()
    },
  })

  const handleClose = () => {
    mutation.reset()
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>グループを削除</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5}>
          {mutation.isError && (
            <Alert severity="error">削除に失敗しました。再度お試しください。</Alert>
          )}
          <Typography variant="body2">
            グループ「<strong>{group?.name}</strong>」を削除しますか？
          </Typography>
          <Typography variant="body2" color="text.secondary">
            チケット自体は削除されません。グループの紐付けのみ解除されます。
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>キャンセル</Button>
        <Button
          variant="contained"
          color="error"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          削除
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ---- ページ本体 -------------------------------------------------------------

/**
 * タスクグループ管理ページ本体。
 * グループの進捗・メンバー確認と、名前編集・削除操作を提供する。
 */
export default function SCR004_TaskGroupPage() {
  const [editTarget, setEditTarget] = useState<TaskGroupItem | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TaskGroupItem | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => taskGroupsApi.getList().then((r) => r.data),
    staleTime: 30 * 1000,
  })

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (isError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">グループ一覧の取得に失敗しました。</Alert>
      </Box>
    )
  }

  const groups = data?.items ?? []

  return (
    <Box sx={{ p: 3 }}>
      {/* ページヘッダー */}
      <Stack direction="row" sx={{ alignItems: 'center', mb: 2 }} spacing={1}>
        <GroupWorkIcon color="secondary" />
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>タスクグループ管理</Typography>
        <Chip label={`${groups.length}件`} size="small" variant="outlined" />
      </Stack>

      <Alert severity="info" sx={{ mb: 3 }}>
        グループの新規作成・チケットの追加はチケット一覧画面から行います。
        チケット行の <GroupWorkIcon fontSize="small" sx={{ verticalAlign: 'middle', mx: 0.5 }} /> アイコンをクリックしてください。
      </Alert>

      {groups.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 6 }}>
          タスクグループはまだありません。
        </Typography>
      )}

      {/* グループカード一覧 */}
      <Stack spacing={2}>
        {groups.map((group) => {
          const progress = calcProgress(group.members)
          const doneCount = group.members.filter((m) => CLOSED_STATUSES.has(m.status)).length

          return (
            <Paper key={group.id} variant="outlined" sx={{ p: 2 }}>
              {/* グループヘッダー: 名前・進捗バッジ・操作ボタン */}
              <Stack direction="row" sx={{ alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                  <GroupWorkIcon fontSize="small" color="secondary" />
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    {group.name}
                  </Typography>
                  <Chip
                    label={`${doneCount} / ${group.member_count} 完了`}
                    size="small"
                    color={progress === 100 ? 'success' : 'secondary'}
                    variant={progress === 100 ? 'filled' : 'outlined'}
                  />
                </Stack>
                <Stack direction="row" spacing={0.5}>
                  <Tooltip title="グループ名を編集">
                    <IconButton
                      size="small"
                      onClick={() => setEditTarget(group)}
                      aria-label="グループ名を編集"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="グループを削除">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => setDeleteTarget(group)}
                      aria-label="グループを削除"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>

              {/* グループ説明 */}
              {group.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1, pl: 3.5 }}>
                  {group.description}
                </Typography>
              )}

              {/* 進捗バー */}
              <Box sx={{ mb: 1.5 }}>
                <Stack direction="row" sx={{ justifyContent: 'space-between', mb: 0.25 }}>
                  <Typography variant="caption" color="text.secondary">進捗</Typography>
                  <Typography
                    variant="caption"
                    color={progress === 100 ? 'success.main' : 'text.secondary'}
                    sx={{ fontWeight: progress === 100 ? 'bold' : 'normal' }}
                  >
                    {progress}%
                  </Typography>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={progress}
                  color={progress === 100 ? 'success' : 'secondary'}
                  sx={{ height: 6, borderRadius: 3 }}
                />
              </Box>

              <Divider sx={{ mb: 1 }} />

              {/* メンバー一覧（チケット ID・製品名・ステータス） */}
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                {group.members.map((m) => (
                  <Chip
                    key={m.ticket_id}
                    label={`#${m.ticket_id} ${m.product_name}`}
                    size="small"
                    variant="outlined"
                    color={CLOSED_STATUSES.has(m.status) ? 'default' : (STATUS_COLOR[m.status] ?? 'default')}
                    sx={{
                      height: 20,
                      fontSize: '0.68rem',
                      opacity: CLOSED_STATUSES.has(m.status) ? 0.65 : 1,
                    }}
                    title={`${m.subject} — ${STATUS_LABEL[m.status] ?? m.status}`}
                  />
                ))}
              </Stack>
            </Paper>
          )
        })}
      </Stack>

      {/* ダイアログ群 */}
      <EditGroupDialog group={editTarget} onClose={() => setEditTarget(null)} />
      <DeleteGroupDialog group={deleteTarget} onClose={() => setDeleteTarget(null)} />
    </Box>
  )
}
