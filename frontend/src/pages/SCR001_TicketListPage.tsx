/**
 * チケット一覧ページ（SCR-T001）。
 * チケットを製品単位でグループ化し、フェーズ行・折りたたみ可能な 3 階層ツリーで表示する。
 * 仕様ソース: docs/ 未定義（初期実装）
 * 業務制約: tracker="phase" は製品グループ内のグループ行として表示する。親子関係は depth <= 3 まで。
 */
import React, { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  LinearProgress,
  ListSubheader,
  MenuItem,
  Pagination,
  Paper,
  Select,
  Skeleton,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight'
import FolderIcon from '@mui/icons-material/Folder'
import SearchIcon from '@mui/icons-material/Search'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined'
import GroupWorkIcon from '@mui/icons-material/GroupWork'
import LinkOffIcon from '@mui/icons-material/LinkOff'
import { productReleasesApi, productsApi, projectsApi, taskGroupsApi, ticketsApi } from '../api/endpoints/apis'
import type {
  GroupMemberSummary,
  ProductItem,
  ProductReleaseCreateRequest,
  ProductReleaseItem,
  ProductResponse,
  ReleaseStatus,
  ReleaseType,
  TaskGroupCreateRequest,
  TaskGroupItem,
  TicketCreateRequest,
  TicketListQuery,
  TicketPriority,
  TicketResponse,
  TicketStatus,
  TicketTracker,
  TicketUpdateRequest,
} from '../api/endpoints/types'

const QUERY_KEY = ['tickets', 'list'] as const
/** "すべて" タブの識別値。project_id フィルタなしに対応する。 */
const ALL_PROJECTS_TAB = '__all__' as const
/** テーブルの列数（製品グループヘッダーの colSpan に使用） */
const COL_COUNT = 9

const STATUS_LABEL: Record<TicketStatus, string> = {
  new: '新規',
  in_progress: '進行中',
  resolved: '解決済み',
  closed: '終了',
  rejected: '却下',
}
const STATUS_COLOR: Record<TicketStatus, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
  new: 'info',
  in_progress: 'warning',
  resolved: 'success',
  closed: 'default',
  rejected: 'error',
}
const PRIORITY_LABEL: Record<TicketPriority, string> = {
  urgent: '緊急',
  high: '高',
  normal: '通常',
  low: '低',
}
const PRIORITY_COLOR: Record<TicketPriority, string> = {
  urgent: '#B91C1C',
  high: '#B45309',
  normal: '#1A202C',
  low: '#718096',
}
const TRACKER_LABEL: Record<TicketTracker, string> = {
  bug: 'バグ',
  feature: '機能',
  support: 'サポート',
  task: 'タスク',
  phase: 'フェーズ',
}

/**
 * 作業サイクル種別の表示ラベル。
 * co-change: app/models/product.py RELEASE_TYPE_* 定数
 */
const RELEASE_TYPE_LABEL: Record<ReleaseType, string> = {
  initial: '初回リリース',
  spec_change: '仕様変更',
  version_upgrade: 'バージョンアップ',
  maintenance: '保守',
}

/**
 * 作業サイクル種別の Chip カラー。
 * co-change: app/models/product.py RELEASE_TYPE_* 定数
 */
const RELEASE_TYPE_COLOR: Record<ReleaseType, 'default' | 'primary' | 'info' | 'warning'> = {
  initial: 'primary',
  spec_change: 'warning',
  version_upgrade: 'info',
  maintenance: 'default',
}

/**
 * 作業サイクル進捗の表示ラベル。
 * co-change: app/models/product.py RELEASE_STATUS_* 定数
 */
const RELEASE_STATUS_LABEL: Record<ReleaseStatus, string> = {
  planning: '計画中',
  in_progress: '進行中',
  completed: '完了',
}

/**
 * 作業サイクル進捗の Chip カラー。リリース前後の識別表示に使用する。
 * completed(リリース済み)=緑、in_progress=橙、planning=デフォルト灰
 * co-change: app/models/product.py RELEASE_STATUS_* 定数
 */
const RELEASE_STATUS_CHIP_COLOR: Record<ReleaseStatus, 'default' | 'success' | 'warning'> = {
  planning: 'default',
  in_progress: 'warning',
  completed: 'success',
}

/**
 * 完了扱いとするステータス。
 * Set を使用して O(1) ルックアップを保証する。期限超過判定・行透過度の 2 箇所で参照する。
 */
const CLOSED_STATUSES = new Set<TicketStatus>(['resolved', 'closed', 'rejected'])

/** 期限超過かどうかを判定する。完了済みステータスは超過扱いとしない。 */
function isOverdue(dueDate: string | null, status: TicketStatus): boolean {
  if (dueDate === null) return false
  if (CLOSED_STATUSES.has(status)) return false
  return dueDate < new Date().toISOString().slice(0, 10)
}

/** 製品グループ型 */
interface ProductGroup {
  product: ProductResponse
  /** tracker="phase" のルートチケット（フェーズ） */
  phaseTickets: TicketResponse[]
  /** フェーズに属さないルートチケット（tracker != "phase"） */
  rootTickets: TicketResponse[]
  /** 親チケット ID → 子チケット一覧（全深度共通） */
  childrenMap: Map<number, TicketResponse[]>
  /** グループ内の全チケット数（ヘッダー件数表示用） */
  totalCount: number
}

// ---- 作業サイクルタブ行 -------------------------------------------------------

interface ReleaseTabRowProps {
  product: ProductResponse
  releases: ProductReleaseItem[]
  selectedReleaseId: number | null
  onSelectRelease: (releaseId: number | null) => void
  onCreateRelease: () => void
}

/**
 * 作業サイクルチップ 1 個を描画するヘルパー。ReleaseTabRow から切り出して再利用する。
 */
function ReleaseCycleChip({ r, selectedReleaseId, onSelectRelease }: {
  r: ProductReleaseItem
  selectedReleaseId: number | null
  onSelectRelease: (id: number | null) => void
}) {
  return (
    <Chip
      key={r.id}
      label={r.name}
      size="small"
      variant={selectedReleaseId === r.id ? 'filled' : 'outlined'}
      color={selectedReleaseId === r.id ? RELEASE_TYPE_COLOR[r.release_type] : 'default'}
      onClick={() => onSelectRelease(r.id)}
      icon={r.status === 'completed' ? <CheckCircleOutlineIcon sx={{ fontSize: '0.9rem !important' }} /> : undefined}
      title={`${RELEASE_TYPE_LABEL[r.release_type]} / ${RELEASE_STATUS_LABEL[r.status]}${r.target_date ? ' / 目標: ' + r.target_date : ''}`}
      sx={{
        height: 22,
        fontSize: '0.72rem',
        cursor: 'pointer',
        opacity: r.status === 'completed' ? 0.7 : 1,
      }}
    />
  )
}

/**
 * 製品グループ内に表示する作業サイクル（リリース）選択タブ行。
 *
 * 初回リリース（release_type="initial"）と追加サイクル（仕様変更・バージョンアップ・保守）を
 * 視覚的に分離して表示する。「すべて」で全件フィルタ解除。
 * 完了サイクルはアイコン＋透過で視覚的に区別する。
 */
function ReleaseTabRow({ releases, selectedReleaseId, onSelectRelease, onCreateRelease }: ReleaseTabRowProps) {
  /** 初回リリースグループ（release_type=initial） */
  const initialReleases = releases.filter((r) => r.release_type === 'initial')
  /** 追加サイクルグループ（仕様変更・バージョンアップ・保守） */
  const otherReleases = releases.filter((r) => r.release_type !== 'initial')

  return (
    <Box sx={{ backgroundColor: '#F5F8FF', py: 0.75, px: 2, borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
      <Stack direction="row" spacing={0} sx={{ alignItems: 'stretch', flexWrap: 'wrap', gap: '4px 0' }}>

        {/* ---- 初回リリース グループ ---- */}
        <Stack
          direction="row"
          spacing={0.75}
          sx={{
            alignItems: 'center',
            flexWrap: 'wrap',
            border: '1px solid',
            borderColor: 'primary.light',
            borderRadius: '6px',
            px: 1,
            py: 0.25,
            mr: 1,
            bgcolor: 'primary.50',
          }}
        >
          {/* セクションタグ */}
          <Box
            component="span"
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              fontSize: '0.65rem',
              fontWeight: 'bold',
              px: 0.75,
              py: 0.15,
              borderRadius: '4px',
              whiteSpace: 'nowrap',
              mr: 0.25,
            }}
          >
            初回
          </Box>

          {/* "すべて" タブ */}
          <Chip
            label="すべて"
            size="small"
            variant={selectedReleaseId === null ? 'filled' : 'outlined'}
            color={selectedReleaseId === null ? 'primary' : 'default'}
            onClick={() => onSelectRelease(null)}
            sx={{ height: 22, fontSize: '0.72rem', cursor: 'pointer' }}
          />

          {initialReleases.map((r) => (
            <ReleaseCycleChip key={r.id} r={r} selectedReleaseId={selectedReleaseId} onSelectRelease={onSelectRelease} />
          ))}
          {initialReleases.length === 0 && (
            <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic', fontSize: '0.68rem' }}>
              未登録
            </Typography>
          )}
        </Stack>

        {/* ---- 2回目以降 グループ（仕様変更・バージョンアップ・保守） ---- */}
        <Stack
          direction="row"
          spacing={0.75}
          sx={{
            alignItems: 'center',
            flexWrap: 'wrap',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: '6px',
            px: 1,
            py: 0.25,
            mr: 1,
            bgcolor: 'grey.50',
          }}
        >
          {/* セクションタグ */}
          <Box
            component="span"
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              bgcolor: 'text.secondary',
              color: '#fff',
              fontSize: '0.65rem',
              fontWeight: 'bold',
              px: 0.75,
              py: 0.15,
              borderRadius: '4px',
              whiteSpace: 'nowrap',
              mr: 0.25,
            }}
          >
            2回目以降
          </Box>

          {otherReleases.map((r) => (
            <ReleaseCycleChip key={r.id} r={r} selectedReleaseId={selectedReleaseId} onSelectRelease={onSelectRelease} />
          ))}
          {otherReleases.length === 0 && (
            <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic', fontSize: '0.68rem' }}>
              未登録
            </Typography>
          )}
        </Stack>

        {/* 新規サイクル追加ボタン */}
        <Tooltip title="新しい作業サイクルを追加">
          <IconButton
            size="small"
            onClick={(e) => { e.stopPropagation(); onCreateRelease() }}
            aria-label="作業サイクルを追加"
            sx={{ p: 0.25 }}
          >
            <AddIcon sx={{ fontSize: '1rem' }} />
          </IconButton>
        </Tooltip>
      </Stack>
    </Box>
  )
}

// ---- タスクグループ管理ダイアログ -------------------------------------------

interface TaskGroupManagerDialogProps {
  /** 管理対象チケット。null のとき非表示。 */
  ticket: TicketResponse | null
  /** このチケットが現在属しているグループ一覧 */
  groups: TaskGroupItem[]
  /** ページに表示中の全チケット（グループ追加候補に使用） */
  allTickets: TicketResponse[]
  onClose: () => void
}

/**
 * タスクグループ管理ダイアログ。
 * - 現在の所属グループ一覧表示・グループからの離脱
 * - 既存グループへの追加
 * - 新規グループ作成（グループ名 + チケット選択）
 */
function TaskGroupManagerDialog({ ticket, groups, allTickets, onClose }: TaskGroupManagerDialogProps) {
  const open = ticket !== null
  /** 表示タブ: 'current'=所属グループ, 'join'=既存グループへの追加, 'create'=新規グループ作成 */
  const [tab, setTab] = useState<'current' | 'join' | 'create'>('current')
  /** 既存グループへの追加タブで選択中のグループ ID */
  const [selectedGroupIdToJoin, setSelectedGroupIdToJoin] = useState<number | null>(null)
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupDesc, setNewGroupDesc] = useState('')
  /** 新規グループに追加するチケット ID セット（対象チケットは初期選択済み） */
  const [selectedTicketIds, setSelectedTicketIds] = useState<Set<number>>(new Set())

  const queryClient = useQueryClient()

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['task-groups'] })

  const createMutation = useMutation({
    mutationFn: (data: TaskGroupCreateRequest) =>
      taskGroupsApi.create(data).then((r) => r.data),
    onSuccess: () => { invalidate(); handleClose() },
  })

  const removeMutation = useMutation({
    mutationFn: ({ groupId, ticketId }: { groupId: number; ticketId: number }) =>
      taskGroupsApi.removeMembers(groupId, { ticket_ids: [ticketId] }).then((r) => r.data),
    onSuccess: invalidate,
  })

  /** 全グループ一覧（既存グループへの追加タブで使用） */
  const { data: allGroupsData, isLoading: isAllGroupsLoading } = useQuery({
    queryKey: ['task-groups'],
    queryFn: () => taskGroupsApi.getList().then((r) => r.data),
    enabled: open,
    staleTime: 30 * 1000,
  })

  const addToGroupMutation = useMutation({
    mutationFn: ({ groupId, ticketId }: { groupId: number; ticketId: number }) =>
      taskGroupsApi.addMembers(groupId, { ticket_ids: [ticketId] }).then((r) => r.data),
    onSuccess: () => { invalidate(); setSelectedGroupIdToJoin(null) },
  })

  /** 参加可能なグループ（既に所属していないもの） */
  const joinableGroups = (allGroupsData?.items ?? []).filter(
    (g) => !groups.some((existing) => existing.id === g.id)
  )

  const handleClose = () => {
    setTab('current')
    setSelectedGroupIdToJoin(null)
    addToGroupMutation.reset()
    setNewGroupName('')
    setNewGroupDesc('')
    setSelectedTicketIds(new Set())
    createMutation.reset()
    onClose()
  }

  // ダイアログが開いたとき、対象チケット自身を選択済みにする
  React.useEffect(() => {
    if (ticket) {
      setSelectedTicketIds(new Set([ticket.id]))
    }
  }, [ticket?.id])

  const handleCreateGroup = () => {
    if (!ticket || !newGroupName.trim() || selectedTicketIds.size < 2) return
    createMutation.mutate({
      name: newGroupName.trim(),
      description: newGroupDesc.trim() || null,
      ticket_ids: Array.from(selectedTicketIds),
    })
  }

  const toggleTicket = (id: number) => {
    if (!ticket) return
    if (id === ticket.id) return // 起点チケットは外せない
    setSelectedTicketIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 自分以外のチケット（グループ追加候補）
  const candidateTickets = allTickets.filter((t) => t.id !== ticket?.id)

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        タスクグループ管理 — #{ticket?.id} {ticket?.subject}
      </DialogTitle>
      <DialogContent sx={{ pt: 0 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={`所属グループ（${groups.length}件）`} value="current" />
          <Tab label={`既存グループに追加（${joinableGroups.length}件）`} value="join" />
          <Tab label="新規グループ作成" value="create" />
        </Tabs>

        {/* ---- 所属グループ一覧タブ ---- */}
        {tab === 'current' && (
          <Box>
            {groups.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                まだグループに属していません。「新規グループ作成」タブでグループ化できます。
              </Typography>
            ) : (
              groups.map((g) => (
                <Paper key={g.id} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                  <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                      <GroupWorkIcon fontSize="small" color="secondary" />
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{g.name}</Typography>
                      <Chip label={`${g.member_count}件`} size="small" color="secondary" variant="outlined" />
                    </Stack>
                    <Tooltip title="このグループから離脱">
                      <IconButton
                        size="small"
                        color="error"
                        disabled={removeMutation.isPending}
                        onClick={() => ticket && removeMutation.mutate({ groupId: g.id, ticketId: ticket.id })}
                        aria-label="グループから離脱"
                      >
                        <LinkOffIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                  {/* メンバー一覧 */}
                  <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', pl: 3.5 }}>
                    {g.members.map((m: GroupMemberSummary) => (
                      <Chip
                        key={m.ticket_id}
                        label={`#${m.ticket_id} ${m.product_name}`}
                        size="small"
                        variant={m.ticket_id === ticket?.id ? 'filled' : 'outlined'}
                        color={m.ticket_id === ticket?.id ? 'secondary' : 'default'}
                        sx={{ height: 18, fontSize: '0.65rem', mb: 0.5 }}
                        title={m.subject}
                      />
                    ))}
                  </Stack>
                </Paper>
              ))
            )}
          </Box>
        )}

        {/* ---- 既存グループへの追加タブ ---- */}
        {tab === 'join' && (
          <Box>
            {addToGroupMutation.isError && (
              <Alert severity="error" sx={{ mb: 1 }}>追加に失敗しました。再度お試しください。</Alert>
            )}
            {isAllGroupsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : joinableGroups.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                追加できるグループがありません。「新規グループ作成」タブでグループを作成してください。
              </Typography>
            ) : (
              joinableGroups.map((g) => (
                <Paper
                  key={g.id}
                  variant="outlined"
                  onClick={() => setSelectedGroupIdToJoin(g.id === selectedGroupIdToJoin ? null : g.id)}
                  sx={{
                    p: 1.5,
                    mb: 1,
                    cursor: 'pointer',
                    borderColor: selectedGroupIdToJoin === g.id ? 'secondary.main' : 'divider',
                    backgroundColor: selectedGroupIdToJoin === g.id ? 'action.selected' : 'transparent',
                    '&:hover': { backgroundColor: 'action.hover' },
                  }}
                >
                  <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                    <GroupWorkIcon fontSize="small" color="secondary" />
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{g.name}</Typography>
                    <Chip label={`${g.member_count}件`} size="small" color="secondary" variant="outlined" />
                  </Stack>
                  <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', pl: 3.5, mt: 0.5 }}>
                    {g.members.map((m) => (
                      <Chip
                        key={m.ticket_id}
                        label={`#${m.ticket_id} ${m.product_name}`}
                        size="small"
                        variant="outlined"
                        sx={{ height: 18, fontSize: '0.65rem', mb: 0.5 }}
                        title={m.subject}
                      />
                    ))}
                  </Stack>
                </Paper>
              ))
            )}
          </Box>
        )}

        {/* ---- 新規グループ作成タブ ---- */}
        {tab === 'create' && (
          <Stack spacing={2}>
            {createMutation.isError && (
              <Alert severity="error">グループの作成に失敗しました。再度お試しください。</Alert>
            )}
            <TextField
              label="グループ名"
              required
              fullWidth
              size="small"
              placeholder="例: OS v2 移行作業、年末バッチ対応"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              slotProps={{ htmlInput: { maxLength: 200 } }}
              autoFocus
            />
            <TextField
              label="説明（任意）"
              fullWidth
              size="small"
              multiline
              rows={2}
              value={newGroupDesc}
              onChange={(e) => setNewGroupDesc(e.target.value)}
              slotProps={{ htmlInput: { maxLength: 1000 } }}
            />
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                グループ化するチケットを選択（2件以上必須。このチケット #{ticket?.id} は必ず含まれます）
              </Typography>
              <Paper variant="outlined" sx={{ maxHeight: 220, overflow: 'auto', p: 0.5 }}>
                {candidateTickets.length === 0 ? (
                  <Typography variant="caption" color="text.disabled" sx={{ p: 1, display: 'block' }}>
                    表示中のチケットがありません。
                  </Typography>
                ) : (
                  candidateTickets.map((t) => (
                    <Box
                      key={t.id}
                      onClick={() => toggleTicket(t.id)}
                      sx={{
                        display: 'flex', alignItems: 'center', gap: 1,
                        px: 1, py: 0.5, cursor: 'pointer', borderRadius: 1,
                        backgroundColor: selectedTicketIds.has(t.id) ? 'action.selected' : 'transparent',
                        '&:hover': { backgroundColor: 'action.hover' },
                      }}
                    >
                      <Chip
                        label={selectedTicketIds.has(t.id) ? '✓' : '○'}
                        size="small"
                        color={selectedTicketIds.has(t.id) ? 'secondary' : 'default'}
                        variant={selectedTicketIds.has(t.id) ? 'filled' : 'outlined'}
                        sx={{ width: 32, height: 18, fontSize: '0.65rem' }}
                      />
                      <Typography variant="caption" noWrap sx={{ flex: 1 }}>
                        #{t.id} [{t.product.name}] {t.subject}
                      </Typography>
                    </Box>
                  ))
                )}
              </Paper>
              <Typography variant="caption" color={selectedTicketIds.size < 2 ? 'error' : 'text.secondary'} sx={{ mt: 0.5, display: 'block' }}>
                選択中: {selectedTicketIds.size} 件{selectedTicketIds.size < 2 ? '（2件以上選択してください）' : ''}
              </Typography>
            </Box>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>閉じる</Button>
        {tab === 'join' && (
          <Button
            variant="contained"
            color="secondary"
            onClick={() => ticket && selectedGroupIdToJoin !== null && addToGroupMutation.mutate({ groupId: selectedGroupIdToJoin, ticketId: ticket.id })}
            disabled={selectedGroupIdToJoin === null || addToGroupMutation.isPending}
            startIcon={addToGroupMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            グループに追加
          </Button>
        )}
        {tab === 'create' && (
          <Button
            variant="contained"
            onClick={handleCreateGroup}
            disabled={!newGroupName.trim() || selectedTicketIds.size < 2 || createMutation.isPending}
            startIcon={createMutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            グループ作成
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}

// ---- 作業サイクル作成ダイアログ -----------------------------------------------

interface ProductReleaseCreateDialogProps {
  /** 作成対象の製品。null のとき非表示。 */
  product: ProductResponse | null
  onClose: () => void
  onCreated: (release: ProductReleaseItem) => void
}

/**
 * 新しい作業サイクル（初回リリース・仕様変更・バージョンアップ等）を作成するダイアログ。
 * 作成成功時にリリース一覧クエリを無効化して自動リフレッシュする。
 */
function ProductReleaseCreateDialog({ product, onClose, onCreated }: ProductReleaseCreateDialogProps) {
  const open = product !== null
  const [form, setForm] = useState<{
    name: string
    release_type: ReleaseType
    status: ReleaseStatus
    target_date: string
  }>({
    name: '',
    release_type: 'initial',
    status: 'planning',
    target_date: '',
  })

  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (data: ProductReleaseCreateRequest) =>
      productReleasesApi.create(data).then((r) => r.data),
    onSuccess: (created) => {
      // リリース一覧クエリを無効化して再フェッチを促す
      queryClient.invalidateQueries({ queryKey: ['product-releases'] })
      onCreated(created)
      handleClose()
    },
  })

  const handleClose = () => {
    setForm({ name: '', release_type: 'initial', status: 'planning', target_date: '' })
    mutation.reset()
    onClose()
  }

  const handleSubmit = () => {
    if (!product || !form.name.trim()) return
    mutation.mutate({
      product_id: product.id,
      name: form.name.trim(),
      release_type: form.release_type,
      status: form.status,
      target_date: form.target_date || null,
    })
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>作業サイクルを追加</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {mutation.isError && (
            <Alert severity="error">作業サイクルの作成に失敗しました。再度お試しください。</Alert>
          )}
          {product && (
            <Typography variant="body2" color="text.secondary">
              製品: <strong>{product.name}</strong>
            </Typography>
          )}
          <TextField
            label="サイクル名"
            required
            fullWidth
            size="small"
            placeholder="例: v1.0 初回リリース、OS v2 対応、仕様変更 2026-Q2"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            slotProps={{ htmlInput: { maxLength: 200 } }}
            autoFocus
          />
          <FormControl size="small" fullWidth required>
            <InputLabel>種別</InputLabel>
            <Select
              label="種別"
              value={form.release_type}
              onChange={(e) => setForm((prev) => ({ ...prev, release_type: e.target.value as ReleaseType }))}
            >
              {(Object.keys(RELEASE_TYPE_LABEL) as ReleaseType[]).map((t) => (
                <MenuItem key={t} value={t}>{RELEASE_TYPE_LABEL[t]}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel>進捗</InputLabel>
            <Select
              label="進捗"
              value={form.status}
              onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value as ReleaseStatus }))}
            >
              {(Object.keys(RELEASE_STATUS_LABEL) as ReleaseStatus[]).map((s) => (
                <MenuItem key={s} value={s}>{RELEASE_STATUS_LABEL[s]}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="目標完了日（任意）"
            type="date"
            size="small"
            fullWidth
            value={form.target_date}
            onChange={(e) => setForm((prev) => ({ ...prev, target_date: e.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>
          キャンセル
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!form.name.trim() || mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          作成
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// ---- 製品グループヘッダー行 --------------------------------------------------

interface ProductGroupHeaderProps {
  group: ProductGroup
  collapsed: boolean
  onToggle: () => void
}

/** 製品グループの折りたたみ可能なヘッダー行。クリックでグループ全体を展開/折りたたみする。 */
function ProductGroupHeader({ group, collapsed, onToggle }: ProductGroupHeaderProps) {
  return (
    <Box
      onClick={onToggle}
      sx={{
        py: 0.75,
        px: 1,
        backgroundColor: 'grey.50',
        cursor: 'pointer',
        borderBottom: '1px solid',
        borderColor: 'divider',
        '&:hover': { backgroundColor: 'grey.100' },
      }}
    >
      <Stack direction="row" sx={{ alignItems: 'center' }} spacing={0.5}>
        <IconButton size="small" tabIndex={-1} aria-hidden>
          {collapsed
            ? <KeyboardArrowRightIcon fontSize="small" />
            : <KeyboardArrowDownIcon fontSize="small" />}
        </IconButton>
        <FolderIcon fontSize="small" sx={{ color: 'primary.main', mr: 0.5 }} />
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {group.product.name}
        </Typography>
        <Chip
          label={`${group.totalCount} 件`}
          size="small"
          variant="outlined"
          sx={{ ml: 1, height: 18, fontSize: '0.7rem' }}
        />
      </Stack>
    </Box>
  )
}

// ---- フェーズ行 ----------------------------------------------------------

interface PhaseRowProps {
  phase: TicketResponse
  collapsed: boolean
  onToggle: () => void
  /** 編集ボタンクリック時コールバック */
  onEdit?: (ticket: TicketResponse) => void
}

/** フェーズ（tracker="phase"）の折りたたみ可能なグループ行。配下タスクを一括展開/折りたたむ。 */
function PhaseRow({ phase, collapsed, onToggle, onEdit }: PhaseRowProps) {
  return (
    <TableRow
      onClick={onToggle}
      sx={{
        backgroundColor: '#F0F7FF',
        cursor: 'pointer',
        '&:hover': { backgroundColor: '#DDEEFF' },
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <TableCell colSpan={COL_COUNT} sx={{ py: 0.5, pl: 4 }}>
        <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <Stack direction="row" sx={{ alignItems: 'center' }} spacing={0.5}>
            <IconButton size="small" tabIndex={-1} aria-hidden sx={{ p: 0.25 }}>
              {collapsed
                ? <KeyboardArrowRightIcon fontSize="small" />
                : <KeyboardArrowDownIcon fontSize="small" />}
            </IconButton>
            <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'primary.dark' }}>
              {phase.subject}
            </Typography>
            <Chip
              label="フェーズ"
              size="small"
              color="primary"
              variant="outlined"
              sx={{ ml: 0.5, height: 18, fontSize: '0.7rem' }}
            />
            {phase.due_date && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                期日: {phase.due_date}
              </Typography>
            )}
          </Stack>
          {onEdit && (
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); onEdit(phase) }}
              aria-label="フェーズを編集"
              sx={{ mr: 1 }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )}
        </Stack>
      </TableCell>
    </TableRow>
  )
}

// ---- チケット行 -----------------------------------------------------------

interface TicketRowProps {
  ticket: TicketResponse
  /** 階層深度。0=ルート, 1=子, 2=孫, 3=曾孫 */
  depth?: number
  hasChildren?: boolean
  childrenCollapsed?: boolean
  onToggle?: () => void
  /** 編集ボタンクリック時コールバック */
  onEdit?: (ticket: TicketResponse) => void
  /**
   * チケットが属する作業サイクル情報。release_id != null のとき渡す。
   * completed(リリース済み) / in_progress / planning の 3 状態を色とアイコンで識別する。
   */
  release?: ProductReleaseItem
  /**
   * チケットが属するタスクグループ一覧。グループバッジとして題名列に表示する。
   * グループ管理ダイアログの起動にも使用する。
   */
  groups?: TaskGroupItem[]
  /** グループ管理ダイアログを開くコールバック */
  onOpenGroupManager?: (ticket: TicketResponse) => void
}

/** チケット 1 件を表すテーブル行。depth に応じたインデントを付与する。 */
function TicketRow({ ticket, depth = 0, hasChildren = false, childrenCollapsed = false, onToggle, onEdit, release, groups, onOpenGroupManager }: TicketRowProps) {
  const isRoot = depth === 0
  // インデント: depth に応じて増加（子あり=2+depth*3, 子なし=5+depth*3）
  const idCellPl = (hasChildren ? 2 : 5) + depth * 3
  return (
    <TableRow
      hover
      sx={{ opacity: CLOSED_STATUSES.has(ticket.status) ? 0.6 : 1 }}
    >
      <TableCell sx={{ pl: idCellPl }}>
        <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'nowrap' }} spacing={0}>
          {hasChildren && (
            <IconButton
              size="small"
              onClick={onToggle}
              sx={{ mr: 0.25, p: 0.25 }}
              aria-label={childrenCollapsed ? '子チケットを展開' : '子チケットを折りたたむ'}
            >
              {childrenCollapsed
                ? <KeyboardArrowRightIcon fontSize="small" />
                : <KeyboardArrowDownIcon fontSize="small" />}
            </IconButton>
          )}
          <Typography
            variant="body2"
            color={isRoot ? 'primary' : 'text.secondary'}
            sx={{ fontWeight: 'bold' }}
          >
            #{ticket.id}
          </Typography>
        </Stack>
      </TableCell>
      <TableCell>
        <Typography variant="body2" noWrap>{TRACKER_LABEL[ticket.tracker]}</Typography>
      </TableCell>
      <TableCell>
        <Chip
          label={STATUS_LABEL[ticket.status]}
          color={STATUS_COLOR[ticket.status]}
          size="small"
          variant="outlined"
        />
      </TableCell>
      <TableCell>
        <Typography
          variant="body2"
          sx={{ fontWeight: ticket.priority === 'urgent' ? 'bold' : 'normal', color: PRIORITY_COLOR[ticket.priority] }}
        >
          {PRIORITY_LABEL[ticket.priority]}
        </Typography>
      </TableCell>
      <TableCell>
        <Tooltip title={ticket.subject} placement="top-start">
          <Typography
            variant="body2"
            sx={{
              maxWidth: 400,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              cursor: 'default',
              pl: depth > 0 ? depth * 2 : 0,
            }}
          >
            {depth > 0 && (
              <Typography
                component="span"
                variant="body2"
                sx={{ color: 'text.disabled', mr: 0.5, fontSize: '0.75rem' }}
                aria-hidden
              >
                ↳
              </Typography>
            )}
            {ticket.subject}
          </Typography>
        </Tooltip>
        {/* 作業サイクル: リリース前後・進捗状態を識別するチップ */}
        {release && (
          <Box sx={{ mt: 0.25, pl: depth > 0 ? depth * 2 : 0 }}>
            <Chip
              icon={
                release.status === 'completed'
                  ? <CheckCircleOutlineIcon sx={{ fontSize: '0.8rem !important' }} />
                  : undefined
              }
              label={
                release.status === 'completed'
                  ? `${release.name}（リリース済み）`
                  : `${release.name}（${RELEASE_STATUS_LABEL[release.status]}）`
              }
              size="small"
              color={RELEASE_STATUS_CHIP_COLOR[release.status]}
              variant={release.status === 'completed' ? 'filled' : 'outlined'}
              sx={{ height: 16, fontSize: '0.65rem', maxWidth: 260 }}
            />
          </Box>
        )}
        {/* 前後関係: 先行チケット表示 */}
        {ticket.predecessor_ids.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ mt: 0.25, pl: depth > 0 ? depth * 2 : 0, flexWrap: 'wrap' }}>
            {ticket.predecessor_ids.map((pid) => (
              <Chip
                key={pid}
                label={`先行: #${pid}`}
                size="small"
                variant="outlined"
                color="default"
                sx={{ height: 16, fontSize: '0.65rem', borderColor: 'grey.400', color: 'text.secondary' }}
              />
            ))}
          </Stack>
        )}
        {/* タスクグループ: 所属グループのバッジ + 管理ボタン */}
        {(groups && groups.length > 0) && (
          <Stack direction="row" spacing={0.5} sx={{ mt: 0.25, pl: depth > 0 ? depth * 2 : 0, flexWrap: 'wrap', alignItems: 'center' }}>
            {groups.map((g) => (
              <Chip
                key={g.id}
                icon={<GroupWorkIcon sx={{ fontSize: '0.75rem !important' }} />}
                label={`${g.name} (${g.member_count}件)`}
                size="small"
                variant="outlined"
                color="secondary"
                sx={{ height: 16, fontSize: '0.65rem', maxWidth: 200 }}
                onClick={() => onOpenGroupManager?.(ticket)}
                title={`タスクグループ: ${g.name} — クリックでグループ管理`}
              />
            ))}
          </Stack>
        )}
        {/* グループ未登録の場合も管理ボタンを表示（グループ化の起点） */}
        {onOpenGroupManager && (!groups || groups.length === 0) && (
          <Box sx={{ mt: 0.25, pl: depth > 0 ? depth * 2 : 0 }}>
            <Tooltip title="タスクグループに追加">
              <IconButton
                size="small"
                onClick={() => onOpenGroupManager(ticket)}
                sx={{ p: 0.15 }}
                aria-label="タスクグループを管理"
              >
                <GroupWorkIcon sx={{ fontSize: '0.85rem', color: 'text.disabled' }} />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </TableCell>
      <TableCell>
        <Typography variant="body2" color="text.secondary" noWrap>
          {ticket.assignee?.display_name ?? '—'}
        </Typography>
      </TableCell>
      <TableCell>
        <Typography
          variant="body2"
          sx={{
            color: isOverdue(ticket.due_date, ticket.status)
              ? 'error.main'
              : 'text.secondary',
          }}
        >
          {ticket.due_date ?? '—'}
        </Typography>
      </TableCell>
      <TableCell sx={{ textAlign: 'right' }}>
        <Typography variant="body2" color="text.secondary">
          {ticket.done_ratio}%
        </Typography>
      </TableCell>
      <TableCell>
        <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary" noWrap>
            {ticket.updated_at.slice(0, 10)}
          </Typography>
          {onEdit && (
            <IconButton
              size="small"
              onClick={() => onEdit(ticket)}
              aria-label="チケットを編集"
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )}
        </Stack>
      </TableCell>
    </TableRow>
  )
}

// ---- ページ本体 -------------------------------------------------------------

// ---- フィルターパネル --------------------------------------------------------

interface FilterPanelProps {
  filter: TicketListQuery
  onChange: (v: TicketListQuery) => void
  /** 選択中のサイクルチップ一覧。各製品グループで選択されたサイクルを検索条件として表示する。 */
  activeCycleChips: { productId: number; productName: string; releaseName: string }[]
  /** 指定製品のサイクル選択を解除する（「すべて」に戻す） */
  onClearRelease: (productId: number) => void
}

/** チケット一覧の検索・絞り込みパネル。キーワード・ステータス・優先度・トラッカー・サイクルで絞り込む。 */
function FilterPanel({ filter, onChange, activeCycleChips, onClearRelease }: FilterPanelProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap' }} useFlexGap>
        <TextField
          size="small"
          placeholder="題名を検索…"
          value={filter.keyword ?? ''}
          onChange={(e) => onChange({ ...filter, keyword: e.target.value || null, page: 1 })}
          sx={{ minWidth: 220 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>ステータス</InputLabel>
          <Select
            label="ステータス"
            value={filter.status ?? ''}
            onChange={(e) =>
              onChange({ ...filter, status: (e.target.value as TicketStatus) || null, page: 1 })
            }
          >
            <MenuItem value="">すべて</MenuItem>
            {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
              <MenuItem key={s} value={s}>{STATUS_LABEL[s]}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>優先度</InputLabel>
          <Select
            label="優先度"
            value={filter.priority ?? ''}
            onChange={(e) =>
              onChange({ ...filter, priority: (e.target.value as TicketPriority) || null, page: 1 })
            }
          >
            <MenuItem value="">すべて</MenuItem>
            {(Object.keys(PRIORITY_LABEL) as TicketPriority[]).map((p) => (
              <MenuItem key={p} value={p}>{PRIORITY_LABEL[p]}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>トラッカー</InputLabel>
          <Select
            label="トラッカー"
            value={filter.tracker ?? ''}
            onChange={(e) =>
              onChange({ ...filter, tracker: (e.target.value as TicketTracker) || null, page: 1 })
            }
          >
            <MenuItem value="">すべて</MenuItem>
            {(Object.keys(TRACKER_LABEL) as TicketTracker[]).map((t) => (
              <MenuItem key={t} value={t}>{TRACKER_LABEL[t]}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
      {/* 選択中サイクルを検索条件として表示。各製品グループのサイクルタブで選択した絞り込み条件を可視化する。 */}
      {activeCycleChips.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', alignItems: 'center' }} useFlexGap>
          <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
            サイクル絞り込み:
          </Typography>
          {activeCycleChips.map((chip) => (
            <Chip
              key={chip.productId}
              label={`${chip.productName} › ${chip.releaseName}`}
              size="small"
              variant="outlined"
              color="primary"
              onDelete={() => onClearRelease(chip.productId)}
            />
          ))}
        </Stack>
      )}
    </Paper>
  )
}

/**
 * チケット作成ダイアログ。
 * 製品・トラッカー・フェーズ/親チケット（親子関係）・先行チケット（前後関係）・
 * ステータス・優先度・期日を入力して新規チケットを作成する。
 * 作成成功時にチケット一覧クエリを無効化して自動リフレッシュする。
 *
 * 製品を選択するとその製品内のチケットを取得し、フェーズ/親チケット選択と
 * 先行チケット選択（複数可）が有効になる。
 */
interface TicketCreateDialogProps {
  open: boolean
  /** 現在選択中のプロジェクト ID。ALL_PROJECTS_TAB の場合は null。製品リストのフィルタに使用。 */
  projectId: number | null
  onClose: () => void
}

function TicketCreateDialog({ open, projectId, onClose }: TicketCreateDialogProps) {
  const [form, setForm] = useState<{
    product_id: number | ''
    tracker: TicketTracker | ''
    status: TicketStatus
    priority: TicketPriority
    subject: string
    due_date: string
    /** 親チケット ID（フェーズ含む）。'' = なし（ルートレベル） */
    parent_id: number | ''
    /** 先行チケット ID リスト（Finish-to-Start 前後関係） */
    predecessor_ids: number[]
    /** 作業サイクル ID。'' = サイクル未分類 */
    release_id: number | ''
  }>({
    product_id: '',
    tracker: 'task',
    status: 'new',
    priority: 'normal',
    subject: '',
    due_date: '',
    parent_id: '',
    predecessor_ids: [],
    release_id: '',
  })

  const { data: productsData } = useQuery({
    queryKey: ['products', 'list', projectId],
    queryFn: () => productsApi.getList(projectId).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: open,
  })

  /**
   * 製品選択後に候補チケット（フェーズ/親/先行）を取得する。
   * page_size=100: ほとんどの製品はこの範囲内に収まると想定。
   * # TODO(impact): 製品内チケットが 100 件超の場合、候補が切り捨てられる。要確認。
   */
  const { data: productTickets } = useQuery({
    queryKey: ['tickets', 'list', 'create-dialog', form.product_id],
    queryFn: () =>
      ticketsApi.getList({ product_id: form.product_id as number, page_size: 100 }).then((r) => r.data),
    enabled: open && form.product_id !== '',
    staleTime: 30 * 1000,
  })

  /** 製品に紐づく作業サイクル一覧（製品選択後に取得） */
  const { data: releasesData } = useQuery({
    queryKey: ['product-releases', form.product_id],
    queryFn: () => productReleasesApi.getList(form.product_id as number).then((r) => r.data),
    enabled: open && form.product_id !== '',
    staleTime: 60 * 1000,
  })

  /**
   * フェーズチケット（tracker='phase'）。親選択セレクタで最初にグループ表示する。
   * タスクを特定フェーズ配下に登録する際に使用する。
   */
  const phaseTickets = useMemo(
    () => (productTickets?.items ?? []).filter((t) => t.tracker === 'phase'),
    [productTickets],
  )

  /**
   * フェーズ以外で depth < 3 のチケット。親として選択可能。
   * depth=3 のチケットを親にすると depth=4 になり上限を超えるため除外する。
   */
  const otherParentCandidates = useMemo(
    () => (productTickets?.items ?? []).filter((t) => t.tracker !== 'phase' && t.depth < 3),
    [productTickets],
  )

  /** 先行チケット候補: 製品内全チケット。 */
  const predecessorCandidates = productTickets?.items ?? []

  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (data: TicketCreateRequest) => ticketsApi.create(data).then((r) => r.data),
    onSuccess: () => {
      // 作成成功時: チケット一覧を再取得してダイアログを閉じる
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      handleClose()
    },
  })

  const handleClose = () => {
    setForm({
      product_id: '',
      tracker: 'task',
      status: 'new',
      priority: 'normal',
      subject: '',
      due_date: '',
      parent_id: '',
      predecessor_ids: [],
      release_id: '',
    })
    mutation.reset()
    onClose()
  }

  const handleSubmit = () => {
    if (!form.product_id || !form.tracker || !form.subject.trim()) return
    mutation.mutate({
      product_id: form.product_id as number,
      tracker: form.tracker as TicketTracker,
      status: form.status,
      priority: form.priority,
      subject: form.subject.trim(),
      due_date: form.due_date || null,
      parent_id: form.parent_id || null,
      predecessor_ids: form.predecessor_ids,
      release_id: form.release_id || null,
    })
  }

  const isSubmittable = Boolean(form.product_id && form.tracker && form.subject.trim())

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>タスクを追加</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {mutation.isError && (
            <Alert severity="error">チケットの作成に失敗しました。再度お試しください。</Alert>
          )}
          <TextField
            label="題名"
            required
            fullWidth
            size="small"
            value={form.subject}
            onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
            slotProps={{ htmlInput: { maxLength: 500 } }}
            autoFocus
          />
          <Stack direction="row" spacing={2}>
            <FormControl size="small" fullWidth required>
              <InputLabel>製品</InputLabel>
              <Select
                label="製品"
                value={form.product_id}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    product_id: e.target.value as number,
                    // 製品変更時は親・先行チケット選択・作業サイクルをリセットする
                    parent_id: '',
                    predecessor_ids: [],
                    release_id: '',
                  }))
                }
              >
                {(productsData?.items ?? []).map((p: ProductItem) => (
                  <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" fullWidth required>
              <InputLabel>トラッカー</InputLabel>
              <Select
                label="トラッカー"
                value={form.tracker}
                onChange={(e) => setForm((prev) => ({ ...prev, tracker: e.target.value as TicketTracker }))}
              >
                {(Object.keys(TRACKER_LABEL) as TicketTracker[]).map((tr) => (
                  <MenuItem key={tr} value={tr}>{TRACKER_LABEL[tr]}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          {/* フェーズ/親チケット（親子関係）・先行チケット（前後関係） */}
          {/* 製品未選択時は disabled。製品を選択すると候補が読み込まれる。 */}
          <FormControl size="small" fullWidth disabled={!form.product_id}>
            <InputLabel>フェーズ / 親チケット（任意）</InputLabel>
            <Select
              label="フェーズ / 親チケット（任意）"
              value={form.parent_id}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, parent_id: e.target.value as number | '' }))
              }
            >
              <MenuItem value="">なし（ルートレベル）</MenuItem>
              {phaseTickets.length > 0 && <ListSubheader>── フェーズ ──</ListSubheader>}
              {phaseTickets.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>{t.subject}</Typography>
                </MenuItem>
              ))}
              {otherParentCandidates.length > 0 && <ListSubheader>── その他チケット ──</ListSubheader>}
              {otherParentCandidates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>#{t.id} {t.subject}</Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth disabled={!form.product_id}>
            <InputLabel>先行チケット（前後関係・任意）</InputLabel>
            <Select
              multiple
              label="先行チケット（前後関係・任意）"
              value={form.predecessor_ids}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  predecessor_ids: e.target.value as unknown as number[],
                }))
              }
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {(selected as number[]).map((id) => (
                    <Chip key={id} label={`#${id}`} size="small" />
                  ))}
                </Box>
              )}
            >
              {predecessorCandidates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>#{t.id} {t.subject}</Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {/* 作業サイクル（製品選択後に有効化） */}
          <FormControl size="small" fullWidth disabled={!form.product_id}>
            <InputLabel>作業サイクル（任意）</InputLabel>
            <Select
              label="作業サイクル（任意）"
              value={form.release_id}
              onChange={(e) => setForm((prev) => ({ ...prev, release_id: e.target.value as number | '' }))}
            >
              <MenuItem value="">なし（サイクル未分類）</MenuItem>
              {(releasesData?.items ?? []).map((r: ProductReleaseItem) => (
                <MenuItem key={r.id} value={r.id}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                    <Typography variant="body2" noWrap>{r.name}</Typography>
                    <Chip label={RELEASE_TYPE_LABEL[r.release_type]} size="small" variant="outlined" />
                  </Stack>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Stack direction="row" spacing={2}>
            <FormControl size="small" fullWidth>
              <InputLabel>ステータス</InputLabel>
              <Select
                label="ステータス"
                value={form.status}
                onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value as TicketStatus }))}
              >
                {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
                  <MenuItem key={s} value={s}>{STATUS_LABEL[s]}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" fullWidth>
              <InputLabel>優先度</InputLabel>
              <Select
                label="優先度"
                value={form.priority}
                onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value as TicketPriority }))}
              >
                {(Object.keys(PRIORITY_LABEL) as TicketPriority[]).map((p) => (
                  <MenuItem key={p} value={p}>{PRIORITY_LABEL[p]}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <TextField
            label="期日"
            type="date"
            size="small"
            fullWidth
            value={form.due_date}
            onChange={(e) => setForm((prev) => ({ ...prev, due_date: e.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>
          キャンセル
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!isSubmittable || mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          作成
        </Button>
      </DialogActions>
    </Dialog>
  )
}

/**
 * チケット編集ダイアログ。
 * 既存チケットの内容をプリセットした状態で開き、全編集可能フィールドを更新できる。
 * product_id は変更不可（チケットの所属製品移動は別操作とする）。
 * 更新成功時にチケット一覧クエリを無効化して自動リフレッシュする。
 */
interface TicketEditDialogProps {
  /** null のとき非表示 */
  ticket: TicketResponse | null
  onClose: () => void
}

function TicketEditDialog({ ticket, onClose }: TicketEditDialogProps) {
  const open = ticket !== null

  const [form, setForm] = useState<{
    tracker: TicketTracker | ''
    status: TicketStatus
    priority: TicketPriority
    subject: string
    due_date: string
    done_ratio: number
    parent_id: number | ''
    predecessor_ids: number[]
    /** 作業サイクル ID。'' = サイクル未分類 */
    release_id: number | ''
  }>({
    tracker: 'task',
    status: 'new',
    priority: 'normal',
    subject: '',
    due_date: '',
    done_ratio: 0,
    parent_id: '',
    predecessor_ids: [],
    release_id: '',
  })

  // ticket が変わるたびにフォームをリセットする
  const prevTicketIdRef = React.useRef<number | null>(null)
  if (ticket !== null && ticket.id !== prevTicketIdRef.current) {
    prevTicketIdRef.current = ticket.id
    form.tracker = ticket.tracker
    form.status = ticket.status
    form.priority = ticket.priority
    form.subject = ticket.subject
    form.due_date = ticket.due_date ?? ''
    form.done_ratio = ticket.done_ratio
    form.parent_id = ticket.parent_id ?? ''
    form.predecessor_ids = ticket.predecessor_ids
    form.release_id = ticket.release_id ?? ''
  }

  /**
   * 製品内チケット取得（親・先行候補用）。
   * # TODO(impact): 製品内チケットが 100 件超の場合、候補が切り捨てられる。要確認。
   */
  const { data: productTickets } = useQuery({
    queryKey: ['tickets', 'list', 'edit-dialog', ticket?.product.id],
    queryFn: () =>
      ticketsApi.getList({ product_id: ticket!.product.id, page_size: 100 }).then((r) => r.data),
    enabled: open,
    staleTime: 30 * 1000,
  })

  /** 製品に紐づく作業サイクル一覧（編集時の選択用） */
  const { data: editReleasesData } = useQuery({
    queryKey: ['product-releases', ticket?.product.id],
    queryFn: () => productReleasesApi.getList(ticket!.product.id).then((r) => r.data),
    enabled: open,
    staleTime: 60 * 1000,
  })

  /** フェーズチケット（親選択用） */
  const phaseTickets = useMemo(
    () => (productTickets?.items ?? []).filter((t) => t.tracker === 'phase' && t.id !== ticket?.id),
    [productTickets, ticket],
  )

  /** フェーズ以外で depth < 3 のチケット（親選択用・自分自身は除外） */
  const otherParentCandidates = useMemo(
    () =>
      (productTickets?.items ?? []).filter(
        (t) => t.tracker !== 'phase' && t.depth < 3 && t.id !== ticket?.id,
      ),
    [productTickets, ticket],
  )

  /** 先行チケット候補（自分自身は除外） */
  const predecessorCandidates = useMemo(
    () => (productTickets?.items ?? []).filter((t) => t.id !== ticket?.id),
    [productTickets, ticket],
  )

  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (data: TicketUpdateRequest) =>
      ticketsApi.update(ticket!.id, data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY })
      onClose()
    },
  })

  const handleClose = () => {
    mutation.reset()
    onClose()
  }

  const handleSubmit = () => {
    if (!form.tracker || !form.subject.trim()) return
    mutation.mutate({
      tracker: form.tracker as TicketTracker,
      status: form.status,
      priority: form.priority,
      subject: form.subject.trim(),
      due_date: form.due_date || null,
      done_ratio: form.done_ratio,
      parent_id: form.parent_id || null,
      predecessor_ids: form.predecessor_ids,
      release_id: form.release_id || null,
    })
  }

  const isSubmittable = Boolean(form.tracker && form.subject.trim())

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>チケットを編集 {ticket && `#${ticket.id}`}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {mutation.isError && (
            <Alert severity="error">チケットの更新に失敗しました。再度お試しください。</Alert>
          )}
          <TextField
            label="題名"
            required
            fullWidth
            size="small"
            value={form.subject}
            onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
            slotProps={{ htmlInput: { maxLength: 500 } }}
            autoFocus
          />
          <FormControl size="small" fullWidth required>
            <InputLabel>トラッカー</InputLabel>
            <Select
              label="トラッカー"
              value={form.tracker}
              onChange={(e) => setForm((prev) => ({ ...prev, tracker: e.target.value as TicketTracker }))}
            >
              {(Object.keys(TRACKER_LABEL) as TicketTracker[]).map((tr) => (
                <MenuItem key={tr} value={tr}>{TRACKER_LABEL[tr]}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel>フェーズ / 親チケット（任意）</InputLabel>
            <Select
              label="フェーズ / 親チケット（任意）"
              value={form.parent_id}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, parent_id: e.target.value as number | '' }))
              }
            >
              <MenuItem value="">なし（ルートレベル）</MenuItem>
              {phaseTickets.length > 0 && <ListSubheader>── フェーズ ──</ListSubheader>}
              {phaseTickets.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>{t.subject}</Typography>
                </MenuItem>
              ))}
              {otherParentCandidates.length > 0 && <ListSubheader>── その他チケット ──</ListSubheader>}
              {otherParentCandidates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>#{t.id} {t.subject}</Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel>先行チケット（前後関係・任意）</InputLabel>
            <Select
              multiple
              label="先行チケット（前後関係・任意）"
              value={form.predecessor_ids}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  predecessor_ids: e.target.value as unknown as number[],
                }))
              }
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {(selected as number[]).map((id) => (
                    <Chip key={id} label={`#${id}`} size="small" />
                  ))}
                </Box>
              )}
            >
              {predecessorCandidates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  <Typography variant="body2" noWrap>#{t.id} {t.subject}</Typography>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {/* 作業サイクル（現在の製品に紐づくサイクル一覧） */}
          <FormControl size="small" fullWidth>
            <InputLabel>作業サイクル（任意）</InputLabel>
            <Select
              label="作業サイクル（任意）"
              value={form.release_id}
              onChange={(e) => setForm((prev) => ({ ...prev, release_id: e.target.value as number | '' }))}
            >
              <MenuItem value="">なし（サイクル未分類）</MenuItem>
              {(editReleasesData?.items ?? []).map((r: ProductReleaseItem) => (
                <MenuItem key={r.id} value={r.id}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                    <Typography variant="body2" noWrap>{r.name}</Typography>
                    <Chip label={RELEASE_TYPE_LABEL[r.release_type]} size="small" variant="outlined" />
                  </Stack>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Stack direction="row" spacing={2}>
            <FormControl size="small" fullWidth>
              <InputLabel>ステータス</InputLabel>
              <Select
                label="ステータス"
                value={form.status}
                onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value as TicketStatus }))}
              >
                {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
                  <MenuItem key={s} value={s}>{STATUS_LABEL[s]}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" fullWidth>
              <InputLabel>優先度</InputLabel>
              <Select
                label="優先度"
                value={form.priority}
                onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value as TicketPriority }))}
              >
                {(Object.keys(PRIORITY_LABEL) as TicketPriority[]).map((p) => (
                  <MenuItem key={p} value={p}>{PRIORITY_LABEL[p]}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <Stack direction="row" spacing={2}>
            <TextField
              label="期日"
              type="date"
              size="small"
              fullWidth
              value={form.due_date}
              onChange={(e) => setForm((prev) => ({ ...prev, due_date: e.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="進捗率 (%)"
              type="number"
              size="small"
              fullWidth
              value={form.done_ratio}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  done_ratio: Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0)),
                }))
              }
              slotProps={{ htmlInput: { min: 0, max: 100, step: 10 } }}
            />
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>
          キャンセル
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!isSubmittable || mutation.isPending}
          startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          更新
        </Button>
      </DialogActions>
    </Dialog>
  )
}

/**
 * 先行タスク関係に基づいて同一階層のチケットをトポロジカルソートする。
 *
 * 先行タスクが後続タスクより前に表示されるよう並び替える。
 * 先行タスクが同一リスト外の場合（別製品・別親）は無視する。
 * 循環依存がある場合はカーン法で検出し、残余チケットを末尾に追加する。
 *
 * @param tickets - ソート対象の同一階層チケット一覧
 * @returns トポロジカルソート後のチケット一覧
 */
function sortByPredecessors(tickets: TicketResponse[]): TicketResponse[] {
  if (tickets.length === 0) return tickets
  const ticketIds = new Set(tickets.map((t) => t.id))
  // 入次数: 同一リスト内に存在する先行タスク数
  const inDegree = new Map<number, number>(tickets.map((t) => [t.id, 0]))
  // 隣接リスト: predecessor_id → 後続の successor_id 一覧
  const graph = new Map<number, number[]>(tickets.map((t) => [t.id, []]))

  for (const ticket of tickets) {
    for (const predId of ticket.predecessor_ids) {
      if (ticketIds.has(predId)) {
        inDegree.set(ticket.id, (inDegree.get(ticket.id) ?? 0) + 1)
        graph.get(predId)!.push(ticket.id)
      }
    }
  }

  // カーン法: 入次数 0 のノードをキューに投入して順に処理
  const queue: number[] = []
  for (const [id, degree] of inDegree) {
    if (degree === 0) queue.push(id)
  }

  const ticketMap = new Map(tickets.map((t) => [t.id, t]))
  const result: TicketResponse[] = []

  while (queue.length > 0) {
    const id = queue.shift()!
    result.push(ticketMap.get(id)!)
    for (const successorId of graph.get(id) ?? []) {
      const newDegree = (inDegree.get(successorId) ?? 1) - 1
      inDegree.set(successorId, newDegree)
      if (newDegree === 0) queue.push(successorId)
    }
  }

  // 循環依存が発生した場合（業務上は想定外だが安全策）、残余チケットを末尾に追加する
  if (result.length < tickets.length) {
    const resultIds = new Set(result.map((t) => t.id))
    for (const ticket of tickets) {
      if (!resultIds.has(ticket.id)) result.push(ticket)
    }
  }

  return result
}

/**
 * チケットとその子孫を再帰的にフラット化して TableRow 配列を返す。
 *
 * 表示上のインデント・展開/折りたたみを depth で制御する。
 * depth=3 が上限（バックエンド制約）。それ以上はデータが存在しないため自然に終了する。
 *
 * @param ticket        起点となるチケット
 * @param depth         現在の深度（0=フェーズ直下, 1=子, 2=孫, 3=曾孫）
 * @param childrenMap   親チケット ID → 子チケット一覧（全深度共通）
 * @param collapsedTickets 折りたたまれているチケット ID のセット
 * @param onToggle      展開/折りたたみトグル時のコールバック
 */
function flattenTicketTree(
  ticket: TicketResponse,
  depth: number,
  childrenMap: Map<number, TicketResponse[]>,
  collapsedTickets: Set<number>,
  onToggle: (id: number) => void,
  onEdit?: (ticket: TicketResponse) => void,
  releasesById?: Map<number, ProductReleaseItem>,
  groupsByTicket?: Map<number, TaskGroupItem[]>,
  onOpenGroupManager?: (ticket: TicketResponse) => void,
): React.ReactElement[] {
  const children = childrenMap.get(ticket.id) ?? []
  const hasChildren = children.length > 0
  const isCollapsed = collapsedTickets.has(ticket.id)
  return [
    <TicketRow
      key={ticket.id}
      ticket={ticket}
      depth={depth}
      hasChildren={hasChildren}
      childrenCollapsed={isCollapsed}
      onToggle={hasChildren ? () => onToggle(ticket.id) : undefined}
      onEdit={onEdit}
      release={ticket.release_id != null ? releasesById?.get(ticket.release_id) : undefined}
      groups={groupsByTicket?.get(ticket.id)}
      onOpenGroupManager={onOpenGroupManager}
    />,
    ...(hasChildren && !isCollapsed
      ? children.flatMap((child) =>
        flattenTicketTree(child, depth + 1, childrenMap, collapsedTickets, onToggle, onEdit, releasesById, groupsByTicket, onOpenGroupManager)
      )
      : []),
  ]
}

/**
 * チケット一覧ページ本体。
 * プロジェクトタブ・フィルタ・製品グループ別ツリーテーブルを統合する。
 */
export default function SCR001_TicketListPage() {
  const [searchParams] = useSearchParams()

  /**
   * URL クエリパラメータ ?project_id=N からプロジェクト選択画面経由の初期値を取得する。
   * useState の遅延初期化で mount 時のみ評価する。
   */
  const [filter, setFilter] = useState<TicketListQuery>(() => {
    const pid = searchParams.get('project_id')
    return { page: 1, page_size: 100, ...(pid ? { project_id: parseInt(pid, 10) } : {}) }
  })
  const [activeProjectTab, setActiveProjectTab] = useState<string | number>(() => {
    const pid = searchParams.get('project_id')
    return pid ? parseInt(pid, 10) : ALL_PROJECTS_TAB
  })
  /** 折りたたまれている製品 ID のセット */
  const [collapsedProducts, setCollapsedProducts] = useState<Set<number>>(new Set())
  /** 折りたたまれている親チケット ID のセット（デフォルト: 展開） */
  const [collapsedParentTickets, setCollapsedParentTickets] = useState<Set<number>>(new Set())
  /** チケット作成ダイアログの表示フラグ */
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  /** 編集対象チケット。null のとき編集ダイアログは非表示 */
  const [editingTicket, setEditingTicket] = useState<TicketResponse | null>(null)
  /**
   * 製品 ID → 選択中の作業サイクル ID（null=すべて）。
   * 各製品グループ内でのリリースタブ切り替え状態を管理する。
   */
  const [selectedReleaseByProduct, setSelectedReleaseByProduct] = useState<Map<number, number | null>>(new Map())
  /** 作業サイクル追加ダイアログの対象製品。null のとき非表示。 */
  const [createReleaseProduct, setCreateReleaseProduct] = useState<ProductResponse | null>(null)
  /** グループ管理ダイアログの対象チケット。null のとき非表示。 */
  const [groupManagerTicket, setGroupManagerTicket] = useState<TicketResponse | null>(null)

  const { data: projectsData } = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.getList().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: [...QUERY_KEY, filter],
    queryFn: () => ticketsApi.getList(filter),
    select: (res) => res.data,
  })

  /**
   * チケット一覧に登場する製品 ID 一覧（重複排除）。
   * リリース一覧フェッチの対象を絞り込むために使用する。
   */
  const productIdsInView = useMemo(
    () => [...new Set(data?.items.map((t) => t.product.id) ?? [])],
    [data?.items],
  )

  /**
   * 表示中製品のリリース一覧。製品ごとに個別フェッチして集約する。
   * N+1 API 呼び出し注意: 製品数が多い場合は backend 側でまとめて返す API の追加を検討する。
   * # TODO(impact): 製品数が多い場合のパフォーマンス確認が必要
   */
  const { data: allReleasesData } = useQuery({
    queryKey: ['product-releases', productIdsInView],
    queryFn: async () => {
      const results = await Promise.all(
        productIdsInView.map((pid) => productReleasesApi.getList(pid).then((r) => r.data.items)),
      )
      return results.flat()
    },
    enabled: productIdsInView.length > 0,
    staleTime: 30 * 1000,
  })

  /** 製品 ID → 作業サイクル一覧のマップ */
  const releasesByProduct = useMemo(() => {
    const map = new Map<number, ProductReleaseItem[]>()
    for (const r of allReleasesData ?? []) {
      const list = map.get(r.product_id) ?? []
      list.push(r)
      map.set(r.product_id, list)
    }
    return map
  }, [allReleasesData])

  /**
   * リリース ID → リリース情報のマップ。TicketRow でリリース前後を識別するために使用する。
   * allReleasesData が未ロードの場合は空 Map を返す（チップ非表示）。
   */
  const releasesById = useMemo(
    () => new Map((allReleasesData ?? []).map((r) => [r.id, r])),
    [allReleasesData],
  )

  /**
   * タスクグループ一覧。全グループを取得して ticket_id → グループ一覧マップを構築する。
   * staleTime=30s: チケット更新時に invalidateQueries でリフレッシュする。
   */
  const { data: allGroupsData } = useQuery({
    queryKey: ['task-groups', 'list'],
    queryFn: () => taskGroupsApi.getList().then((r) => r.data.items),
    staleTime: 30 * 1000,
  })

  /**
   * チケット ID → 所属グループ一覧のマップ。
   * TicketRow でグループバッジを表示するために使用する。
   */
  const groupsByTicket = useMemo(() => {
    const map = new Map<number, TaskGroupItem[]>()
    for (const group of allGroupsData ?? []) {
      for (const member of group.members) {
        const list = map.get(member.ticket_id) ?? []
        list.push(group)
        map.set(member.ticket_id, list)
      }
    }
    return map
  }, [allGroupsData])

  /** チケットを製品 ID でグループ化し、各グループ内をフェーズ/ルート/子に分離する。
   * parent_id が同グループ内に存在しないチケットは root として扱う（データ不整合の吸収）。
   * tracker="phase" かつルートレベルのチケットは phaseTickets に分類する。
   * selectedReleaseByProduct で選択中のリリース ID がある場合はそのチケットのみを表示する。
   */
  const productGroups = useMemo<ProductGroup[]>(() => {
    if (!data?.items) return []
    // 第1パス: 製品グループを作成し全チケットを収容
    const productMap = new Map<number, { product: ProductResponse; allTickets: TicketResponse[] }>()
    for (const ticket of data.items) {
      if (!productMap.has(ticket.product.id)) {
        productMap.set(ticket.product.id, { product: ticket.product, allTickets: [] })
      }
      productMap.get(ticket.product.id)!.allTickets.push(ticket)
    }
    // 第2パス: グループ内でフェーズ / ルート / 子に分類
    return Array.from(productMap.values()).map(({ product, allTickets }) => {
      // 選択中の作業サイクル ID でフィルタ（null=すべて表示）
      const selectedRelId = selectedReleaseByProduct.get(product.id) ?? null
      const visibleTickets = selectedRelId === null
        ? allTickets
        : allTickets.filter((t) => t.release_id === selectedRelId)

      const ticketIds = new Set(visibleTickets.map((t) => t.id))
      const phaseTickets: TicketResponse[] = []
      const rootTickets: TicketResponse[] = []
      const childrenMap = new Map<number, TicketResponse[]>()
      for (const ticket of visibleTickets) {
        if (ticket.parent_id === null || !ticketIds.has(ticket.parent_id)) {
          if (ticket.tracker === 'phase') {
            phaseTickets.push(ticket)
          } else {
            rootTickets.push(ticket)
          }
        } else {
          const siblings = childrenMap.get(ticket.parent_id) ?? []
          siblings.push(ticket)
          childrenMap.set(ticket.parent_id, siblings)
        }
      }
      const sortedChildrenMap = new Map<number, TicketResponse[]>()
      for (const [parentId, children] of childrenMap) {
        sortedChildrenMap.set(parentId, sortByPredecessors(children))
      }
      return {
        product,
        phaseTickets: sortByPredecessors(phaseTickets),
        rootTickets: sortByPredecessors(rootTickets),
        childrenMap: sortedChildrenMap,
        totalCount: visibleTickets.length,
      }
    })
  }, [data?.items, selectedReleaseByProduct])

  /**
   * FilterPanel のサイクル絞り込み条件表示用チップ一覧。
   * selectedReleaseByProduct で特定サイクルが選択されている製品のみ表示（null=すべて は除外）。
   */
  const activeCycleChips = useMemo(() => {
    const chips: { productId: number; productName: string; releaseName: string }[] = []
    for (const [productId, releaseId] of selectedReleaseByProduct) {
      if (releaseId === null) continue
      const releases = releasesByProduct.get(productId) ?? []
      const release = releases.find((r) => r.id === releaseId)
      if (!release) continue
      const group = productGroups.find((g) => g.product.id === productId)
      chips.push({
        productId,
        productName: group?.product.name ?? String(productId),
        releaseName: release.name,
      })
    }
    return chips
  }, [selectedReleaseByProduct, releasesByProduct, productGroups])

  /** 指定製品のサイクル選択を解除する。FilterPanel のチップ除去ボタンから呼び出される。 */
  const handleClearRelease = useCallback((productId: number) => {
    setSelectedReleaseByProduct((prev) => {
      const next = new Map(prev)
      next.set(productId, null)
      return next
    })
  }, [])

  /** 製品グループの折りたたみ状態をトグルする。useCallback で参照を安定化し子コンポーネントの不要な再レンダーを抑制する。 */
  const toggleProduct = useCallback((productId: number) => {
    setCollapsedProducts((prev) => {
      const next = new Set(prev)
      if (next.has(productId)) next.delete(productId)
      else next.add(productId)
      return next
    })
  }, [])

  /** チケット（フェーズ含む）の子展開状態をトグルする。useCallback で参照を安定化し子コンポーネントの不要な再レンダーを抑制する。 */
  const toggleParentTicket = useCallback((ticketId: number) => {
    setCollapsedParentTickets((prev) => {
      const next = new Set(prev)
      if (next.has(ticketId)) next.delete(ticketId)
      else next.add(ticketId)
      return next
    })
  }, [])

  /** プロジェクトタブ切り替え。project_id フィルタとページ・折りたたみ・リリース選択状態をリセットする。 */
  const handleProjectTabChange = useCallback((_: React.SyntheticEvent, value: string | number) => {
    setActiveProjectTab(value)
    setCollapsedProducts(new Set())
    setCollapsedParentTickets(new Set())
    setSelectedReleaseByProduct(new Map())
    setFilter((prev) => ({
      ...prev,
      project_id: value === ALL_PROJECTS_TAB ? null : (value as number),
      page: 1,
    }))
  }, [])

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h1">チケット</Typography>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          {data && (
            <Typography variant="body2" color="text.secondary">{data.total} 件</Typography>
          )}
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            タスクを追加
          </Button>
        </Stack>
      </Stack>

      {/* プロジェクトタブ */}
      <Paper variant="outlined" sx={{ mb: 2 }}>
        <Tabs
          value={activeProjectTab}
          onChange={handleProjectTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="プロジェクト選択タブ"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="すべて" value={ALL_PROJECTS_TAB} />
          {projectsData?.items.map((proj) => (
            <Tab key={proj.id} label={proj.name} value={proj.id} />
          ))}
        </Tabs>
      </Paper>

      <Box sx={{ mb: 2 }}>
        <FilterPanel
          filter={filter}
          onChange={setFilter}
          activeCycleChips={activeCycleChips}
          onClearRelease={handleClearRelease}
        />
      </Box>
      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>チケット一覧の読み込みに失敗しました。</Alert>
      )}
      {/* 製品グループ別セクション — サイクル選択は各テーブルの上に表示 */}
      <Box>
        {isLoading ? (
          <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
            <LinearProgress />
            <TableContainer>
              <Table size="small" aria-label="チケット一覧">
                <TableHead>
                  <TableRow sx={{ backgroundColor: 'grey.100' }}>
                    <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 100 }}>トラッカー</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 100 }}>ステータス</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 80 }}>優先度</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>題名</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 120 }}>担当者</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 90 }}>期日</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 60, textAlign: 'right' }}>進捗</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 110 }}>更新日時</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: COL_COUNT }).map((__, j) => (
                        <TableCell key={j}><Skeleton variant="text" /></TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        ) : productGroups.length === 0 ? (
          <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                条件に一致するチケットはありません。
              </Typography>
            </Box>
          </Paper>
        ) : (
          <Stack spacing={2}>
            {productGroups.map((group) => {
              const groupCollapsed = collapsedProducts.has(group.product.id)
              const groupReleases = releasesByProduct.get(group.product.id) ?? []
              const selectedRelId = selectedReleaseByProduct.get(group.product.id) ?? null
              const ticketRows = [
                // フェーズチケット（tracker="phase"）を先に表示
                ...group.phaseTickets.flatMap((phase) => {
                  const phaseCollapsed = collapsedParentTickets.has(phase.id)
                  const phaseChildren = group.childrenMap.get(phase.id) ?? []
                  return [
                    <PhaseRow
                      key={`phase-${phase.id}`}
                      phase={phase}
                      collapsed={phaseCollapsed}
                      onToggle={() => toggleParentTicket(phase.id)}
                      onEdit={setEditingTicket}
                    />,
                    ...(!phaseCollapsed
                      ? phaseChildren.flatMap((task) =>
                        flattenTicketTree(task, 1, group.childrenMap, collapsedParentTickets, toggleParentTicket, setEditingTicket, releasesById, groupsByTicket, setGroupManagerTicket)
                      )
                      : []),
                  ]
                }),
                // フェーズに属さないルートチケット
                ...group.rootTickets.flatMap((ticket) =>
                  flattenTicketTree(ticket, 0, group.childrenMap, collapsedParentTickets, toggleParentTicket, setEditingTicket, releasesById, groupsByTicket, setGroupManagerTicket)
                ),
              ]
              return (
                <Paper key={group.product.id} variant="outlined" sx={{ overflow: 'hidden' }}>
                  <ProductGroupHeader
                    group={group}
                    collapsed={groupCollapsed}
                    onToggle={() => toggleProduct(group.product.id)}
                  />
                  {!groupCollapsed && (
                    <>
                      {/* 作業サイクル選択 — チケット一覧の上に表示 */}
                      <ReleaseTabRow
                        product={group.product}
                        releases={groupReleases}
                        selectedReleaseId={selectedRelId}
                        onSelectRelease={(relId) =>
                          setSelectedReleaseByProduct((prev) => {
                            const next = new Map(prev)
                            next.set(group.product.id, relId)
                            return next
                          })
                        }
                        onCreateRelease={() => setCreateReleaseProduct(group.product)}
                      />
                      <TableContainer>
                        <Table size="small" aria-label={`${group.product.name} チケット一覧`}>
                          <TableHead>
                            <TableRow sx={{ backgroundColor: 'grey.100' }}>
                              <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 100 }}>トラッカー</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 100 }}>ステータス</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 80 }}>優先度</TableCell>
                              <TableCell sx={{ fontWeight: 'bold' }}>題名</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 120 }}>担当者</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 90 }}>期日</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 60, textAlign: 'right' }}>進捗</TableCell>
                              <TableCell sx={{ fontWeight: 'bold', width: 110 }}>更新日時</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {ticketRows.length > 0 ? ticketRows : (
                              <TableRow>
                                <TableCell colSpan={COL_COUNT} align="center" sx={{ py: 3 }}>
                                  <Typography variant="body2" color="text.disabled">
                                    このサイクルにはチケットがありません。
                                  </Typography>
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </>
                  )}
                </Paper>
              )
            })}
          </Stack>
        )}
        {data != null && data.total_pages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <Pagination
              count={data.total_pages}
              page={data.page}
              onChange={(_: React.ChangeEvent<unknown>, p: number) =>
                setFilter((prev) => ({ ...prev, page: p }))
              }
              size="small"
              color="primary"
            />
          </Box>
        )}
      </Box>

      {/* タスク追加ダイアログ */}
      <TicketCreateDialog
        open={createDialogOpen}
        projectId={activeProjectTab === ALL_PROJECTS_TAB ? null : (activeProjectTab as number)}
        onClose={() => setCreateDialogOpen(false)}
      />

      {/* チケット編集ダイアログ */}
      <TicketEditDialog
        ticket={editingTicket}
        onClose={() => setEditingTicket(null)}
      />

      {/* 作業サイクル作成ダイアログ（製品グループ内の「＋」ボタンから起動） */}
      <ProductReleaseCreateDialog
        product={createReleaseProduct}
        onClose={() => setCreateReleaseProduct(null)}
        onCreated={(release) => {
          // 作成直後に新しいサイクルを選択状態にする
          setSelectedReleaseByProduct((prev) => {
            const next = new Map(prev)
            next.set(release.product_id, release.id)
            return next
          })
        }}
      />

      {/* タスクグループ管理ダイアログ */}
      <TaskGroupManagerDialog
        ticket={groupManagerTicket}
        groups={groupManagerTicket ? (groupsByTicket.get(groupManagerTicket.id) ?? []) : []}
        allTickets={data?.items ?? []}
        onClose={() => setGroupManagerTicket(null)}
      />
    </Box>
  )
}
