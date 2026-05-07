/**
 * ダッシュボード（SCR-D001）。
 *
 * 表示内容:
 *   1. サマリーカード（期限超過 / 期限 1 週間以内 / 進行中 / 未割当 / TODO）
 *   2. 製品別遅延パネル（遅延件数バッジ）
 *   3. 遅延チケット一覧（due_date < 今日・全件表示・ページネーションなし）
 *   4. 直近1週間チケット一覧（今日 <= due_date <= 7日後・20件/ページ）
 *   5. TODOタスク一覧（未着手・期限なしまたは 1 週間超）
 *
 * データはシステムが自動で浮上させる（「人任せ」を排除）。
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  Box,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Pagination,
  Paper,
  Select,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutlined'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import PersonOffIcon from '@mui/icons-material/PersonOff'
import ChecklistIcon from '@mui/icons-material/Checklist'
import EventBusyIcon from '@mui/icons-material/EventBusy'
import { projectsApi, ticketsApi } from '../api/endpoints/apis'
import type {
  ProductRiskSummary,
  ProjectItem,
  RiskDashboardQuery,
  RiskTicketResponse,
  TicketPriority,
  TicketStatus,
  TicketTracker,
} from '../api/endpoints/types'

const RISK_QUERY_KEY = ['tickets', 'risk-summary'] as const
const PROJECTS_QUERY_KEY = ['projects', 'list'] as const

// ---- 定数 ---------------------------------------------------------------

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

/** テーブルの列数（空行の colSpan に使用） */
const COL_COUNT = 8

/** 直近1週間一覧のページサイズ */
const AT_RISK_PAGE_SIZE = 10

/** TODO タスク一覧のページサイズ */
const TODO_PAGE_SIZE = 10

// ---- サマリーカード -------------------------------------------------------

interface SummaryCardProps {
  label: string
  count: number
  /** 強調表示するしきい値。count がこれ以上なら警告色になる */
  warnThreshold?: number
  icon: React.ReactNode
  description: string
}

function SummaryCard({ label, count, warnThreshold, icon, description }: SummaryCardProps) {
  const isWarning = warnThreshold !== undefined && count >= warnThreshold
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        flex: 1,
        minWidth: 160,
        borderColor: isWarning ? 'warning.main' : 'divider',
        borderWidth: isWarning ? 2 : 1,
      }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.5 }}>
        <Box sx={{ color: isWarning ? 'warning.main' : 'text.secondary', display: 'flex' }}>
          {icon}
        </Box>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Stack>
      <Typography
        variant="h4"
        sx={{ fontWeight: 'bold', color: isWarning ? 'warning.dark' : 'text.primary', lineHeight: 1.2 }}
      >
        {count}
        <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>件</Typography>
      </Typography>
      <Typography variant="caption" color="text.secondary">{description}</Typography>
    </Paper>
  )
}

// ---- 製品別進捗パネル -----------------------------------------------------

interface ProductProgressPanelProps {
  summaries: ProductRiskSummary[]
}

function ProductProgressPanel({ summaries }: ProductProgressPanelProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1.5 }}>製品別遅延状況</Typography>
      <Stack spacing={1.5}>
        {summaries.map((s) => (
          <Stack key={s.product.id} direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <Typography variant="body2" sx={{ fontWeight: 'medium' }}>{s.product.name}</Typography>
              <Chip
                label={`遅延 ${s.overdue_count}件`}
                size="small"
                color={s.overdue_count > 0 ? 'error' : 'default'}
                variant="outlined"
                sx={{ height: 18, fontSize: '0.68rem' }}
              />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {s.total_count}件
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  )
}

// ---- リスクチケット行 -------------------------------------------------------

interface RiskTicketRowProps {
  ticket: RiskTicketResponse
}

function RiskTicketRow({ ticket }: RiskTicketRowProps) {
  const isOverdue = ticket.overdue_days > 0
  const isToday = ticket.overdue_days === 0 && ticket.due_date !== null
  const isNoDueDate = ticket.due_date === null

  return (
    <TableRow
      hover
      sx={{
        backgroundColor: isOverdue ? 'rgba(239,68,68,0.04)' : isToday ? 'rgba(245,158,11,0.04)' : undefined,
      }}
    >
      {/* 期限状態バッジ */}
      <TableCell sx={{ width: 110 }}>
        {isNoDueDate ? (
          <Chip
            icon={<EventBusyIcon />}
            label="期限なし"
            color="default"
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        ) : isOverdue ? (
          <Chip
            icon={<ErrorOutlineIcon />}
            label={`${ticket.overdue_days}日超過`}
            color="error"
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        ) : isToday ? (
          <Chip
            icon={<WarningAmberIcon />}
            label="本日期限"
            color="warning"
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        ) : (
          <Chip
            icon={<AccessTimeIcon />}
            label={`残${Math.abs(ticket.overdue_days)}日`}
            color="default"
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        )}
      </TableCell>
      <TableCell sx={{ width: 60 }}>
        <Typography variant="body2" color="primary" sx={{ fontWeight: 'bold' }}>
          #{ticket.id}
        </Typography>
      </TableCell>
      <TableCell sx={{ width: 80 }}>
        <Typography variant="body2" noWrap>{TRACKER_LABEL[ticket.tracker]}</Typography>
      </TableCell>
      <TableCell sx={{ width: 100 }}>
        <Chip label={STATUS_LABEL[ticket.status]} color={STATUS_COLOR[ticket.status]} size="small" variant="outlined" />
      </TableCell>
      <TableCell sx={{ width: 80 }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: ticket.priority === 'urgent' ? 'bold' : 'normal', color: PRIORITY_COLOR[ticket.priority] }}
        >
          {PRIORITY_LABEL[ticket.priority]}
        </Typography>
      </TableCell>
      <TableCell>
        <Stack spacing={0.25}>
          <Tooltip title={ticket.subject} placement="top-start">
            <Typography
              variant="body2"
              sx={{ maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}
            >
              {ticket.subject}
            </Typography>
          </Tooltip>
          <Typography variant="caption" color="text.secondary">{ticket.product.name}</Typography>
          {/* 前後関係: 先行チケット表示 */}
          {ticket.predecessor_ids.length > 0 && (
            <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap' }}>
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
        </Stack>
      </TableCell>
      <TableCell sx={{ width: 120 }}>
        {ticket.assignee ? (
          <Typography variant="body2" noWrap>{ticket.assignee.display_name}</Typography>
        ) : (
          <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
            <PersonOffIcon fontSize="small" sx={{ color: 'warning.main' }} />
            <Typography variant="body2" color="warning.main">未割当</Typography>
          </Stack>
        )}
      </TableCell>
      <TableCell sx={{ width: 70, textAlign: 'right' }}>
        <Typography variant="body2" color="text.secondary">{ticket.done_ratio}%</Typography>
      </TableCell>
    </TableRow>
  )
}

// ---- ページ本体 -----------------------------------------------------------

export default function SCR003_RiskDashboardPage() {
  const [projectId, setProjectId] = useState<number | ''>('')
  const [atRiskPage, setAtRiskPage] = useState(1)
  const [todoPage, setTodoPage] = useState(1)

  const { data: projectsData } = useQuery({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: () => projectsApi.getList().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const riskQuery: RiskDashboardQuery = useMemo(
    () => ({ ...(projectId !== '' ? { project_id: projectId } : {}) }),
    [projectId],
  )

  const { data, isPending, isError } = useQuery({
    queryKey: [...RISK_QUERY_KEY, riskQuery],
    queryFn: () => ticketsApi.getRiskSummary(riskQuery).then((r) => r.data),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000, // 5 分ごとに自動更新（遅延は時間経過で変化するため）
  })

  const hasOverdueTickets = Boolean(data?.overdue_tickets?.length)
  const hasAtRiskTickets = Boolean(data?.at_risk_tickets?.length)
  const hasTodoTickets = Boolean(data?.todo_tickets?.length)

  /** 直近1週間一覧の現在ページスライス */
  const pagedAtRiskTickets = data?.at_risk_tickets.slice(
    (atRiskPage - 1) * AT_RISK_PAGE_SIZE,
    atRiskPage * AT_RISK_PAGE_SIZE,
  ) ?? []
  const atRiskTotalPages = Math.ceil((data?.at_risk_tickets.length ?? 0) / AT_RISK_PAGE_SIZE)

  /** TODO タスク一覧の現在ページスライス */
  const pagedTodoTickets = data?.todo_tickets.slice(
    (todoPage - 1) * TODO_PAGE_SIZE,
    todoPage * TODO_PAGE_SIZE,
  ) ?? []
  const todoTotalPages = Math.ceil((data?.todo_tickets.length ?? 0) / TODO_PAGE_SIZE)

  return (
    <Box sx={{ p: 3 }}>
      {/* ページヘッダー */}
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>ダッシュボード</Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>プロジェクト</InputLabel>
          <Select value={projectId} label="プロジェクト" onChange={(e) => setProjectId(e.target.value as number | '')}>
            <MenuItem value="">すべて</MenuItem>
            {projectsData?.items.map((p: ProjectItem) => (
              <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>データの取得に失敗しました。再読み込みしてください。</Alert>
      )}

      {/* サマリーカード */}
      {isPending ? (
        <Stack direction="row" spacing={2} sx={{ mb: 3, flexWrap: 'wrap' }} useFlexGap>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height={100} sx={{ flex: 1, minWidth: 160, borderRadius: 1 }} />
          ))}
        </Stack>
      ) : data ? (
        <Stack direction="row" spacing={2} sx={{ mb: 3, flexWrap: 'wrap' }} useFlexGap>
          <SummaryCard
            label="期限超過"
            count={data.summary.overdue_count}
            warnThreshold={1}
            icon={<ErrorOutlineIcon />}
            description="未完了チケットのうち期限を過ぎたもの"
          />
          <SummaryCard
            label="期限 1 週間以内"
            count={data.summary.at_risk_count}
            warnThreshold={5}
            icon={<WarningAmberIcon />}
            description="今後 1 週間以内に期限が来る未完了チケット"
          />
          <SummaryCard
            label="進行中"
            count={data.summary.in_progress_count}
            icon={<AccessTimeIcon />}
            description="new + in_progress ステータスの合計"
          />
          <SummaryCard
            label="担当者未割当"
            count={data.summary.unassigned_count}
            warnThreshold={1}
            icon={<PersonOffIcon />}
            description="未完了チケットのうち担当者がいないもの"
          />
          <SummaryCard
            label="TODOタスク"
            count={data.summary.todo_count}
            icon={<ChecklistIcon />}
            description="未着手（期限なしまたは 1 週間超）のタスク"
          />
        </Stack>
      ) : null}

      {/* 製品別進捗 */}
      {isPending ? (
        <Skeleton variant="rectangular" height={200} sx={{ mb: 3, borderRadius: 1 }} />
      ) : data?.product_summaries.length ? (
        <Box sx={{ mb: 3 }}>
          <ProductProgressPanel summaries={data.product_summaries} />
        </Box>
      ) : null}

      {/* 遅延チケット一覧（全件表示・ページネーションなし） */}
      <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider', backgroundColor: 'grey.50' }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <ErrorOutlineIcon fontSize="small" color="error" />
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              遅延チケット一覧
            </Typography>
            {data && (
              <Chip
                label={`${data.overdue_tickets.length} 件`}
                size="small"
                color="error"
                variant="outlined"
                sx={{ height: 18, fontSize: '0.7rem' }}
              />
            )}
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              ※ 期日昇順・担当者未割当優先。全件表示
            </Typography>
          </Stack>
        </Box>
        <TableContainer>
          <Table size="small" aria-label="遅延チケット一覧">
            <TableHead>
              <TableRow sx={{ backgroundColor: 'grey.100' }}>
                <TableCell sx={{ fontWeight: 'bold', width: 110 }}>期限状態</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>トラッカー</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 100 }}>ステータス</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>優先度</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>題名 / 製品</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 120 }}>担当者</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 70, textAlign: 'right' }}>進捗</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isPending
                ? Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COL_COUNT }).map((__, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))
                : hasOverdueTickets
                  ? data!.overdue_tickets.map((ticket) => (
                    <RiskTicketRow key={ticket.id} ticket={ticket} />
                  ))
                  : (
                    <TableRow>
                      <TableCell colSpan={COL_COUNT} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="success.main" sx={{ fontWeight: 'medium' }}>
                          期限超過のチケットはありません ✓
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 直近1週間チケット一覧（20件/ページ） */}
      <Paper variant="outlined" sx={{ overflow: 'hidden', mt: 3 }}>
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider', backgroundColor: 'grey.50' }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <WarningAmberIcon fontSize="small" color="warning" />
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              直近1週間チケット一覧
            </Typography>
            {data && (
              <Chip
                label={`${data.at_risk_tickets.length} 件`}
                size="small"
                variant="outlined"
                sx={{ height: 18, fontSize: '0.7rem' }}
              />
            )}
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              ※ 今日〜7日以内に期限が来るチケット。期日昇順・担当者未割当優先
            </Typography>
          </Stack>
        </Box>
        <TableContainer>
          <Table size="small" aria-label="直近1週間チケット一覧">
            <TableHead>
              <TableRow sx={{ backgroundColor: 'grey.100' }}>
                <TableCell sx={{ fontWeight: 'bold', width: 110 }}>期限状態</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>トラッカー</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 100 }}>ステータス</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>優先度</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>題名 / 製品</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 120 }}>担当者</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 70, textAlign: 'right' }}>進捗</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isPending
                ? Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COL_COUNT }).map((__, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))
                : hasAtRiskTickets
                  ? pagedAtRiskTickets.map((ticket) => (
                    <RiskTicketRow key={ticket.id} ticket={ticket} />
                  ))
                  : (
                    <TableRow>
                      <TableCell colSpan={COL_COUNT} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="success.main" sx={{ fontWeight: 'medium' }}>
                          直近1週間に期限が来るチケットはありません ✓
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
            </TableBody>
          </Table>
        </TableContainer>
        {/* ページネーション（直近1週間一覧） */}
        {!isPending && atRiskTotalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 1.5, borderTop: 1, borderColor: 'divider' }}>
            <Pagination
              count={atRiskTotalPages}
              page={atRiskPage}
              onChange={(_: React.ChangeEvent<unknown>, p: number) => setAtRiskPage(p)}
              size="small"
              color="primary"
            />
          </Box>
        )}
      </Paper>

      {/* TODO タスク一覧 */}
      <Paper variant="outlined" sx={{ overflow: 'hidden', mt: 3 }}>
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider', backgroundColor: 'grey.50' }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <ChecklistIcon fontSize="small" color="info" />
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
              TODO タスク一覧
            </Typography>
            {data && (
              <Chip
                label={`${data.todo_tickets.length} 件`}
                size="small"
                variant="outlined"
                sx={{ height: 18, fontSize: '0.7rem' }}
              />
            )}
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              ※ 未着手（status=new）かつ期限なしまたは 1 週間超のタスク。優先度順。最大 200 件
            </Typography>
          </Stack>
        </Box>
        <TableContainer>
          <Table size="small" aria-label="TODO タスク一覧">
            <TableHead>
              <TableRow sx={{ backgroundColor: 'grey.100' }}>
                <TableCell sx={{ fontWeight: 'bold', width: 110 }}>期限</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 60 }}>#</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>トラッカー</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 100 }}>ステータス</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>優先度</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>題名 / 製品</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 120 }}>担当者</TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 70, textAlign: 'right' }}>進捗</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isPending
                ? Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COL_COUNT }).map((__, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))
                : hasTodoTickets
                  ? pagedTodoTickets.map((ticket) => (
                    <RiskTicketRow key={ticket.id} ticket={ticket} />
                  ))
                  : (
                    <TableRow>
                      <TableCell colSpan={COL_COUNT} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="success.main" sx={{ fontWeight: 'medium' }}>
                          未着手タスクはありません ✓
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
            </TableBody>
          </Table>
        </TableContainer>
        {/* ページネーション（TODO タスク一覧） */}
        {!isPending && todoTotalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 1.5, borderTop: 1, borderColor: 'divider' }}>
            <Pagination
              count={todoTotalPages}
              page={todoPage}
              onChange={(_: React.ChangeEvent<unknown>, p: number) => setTodoPage(p)}
              size="small"
              color="primary"
            />
          </Box>
        )}
      </Paper>
    </Box>
  )
}
