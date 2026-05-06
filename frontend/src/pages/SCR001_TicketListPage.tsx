/**
 * チケット一覧ページ（SCR-T001）。
 * チケットを製品単位でグループ化し、折りたたみ可能なツリー形式で表示する。
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  Box,
  Chip,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  LinearProgress,
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
import { projectsApi, ticketsApi } from '../api/endpoints/apis'
import type {
  ProductResponse,
  TicketListQuery,
  TicketPriority,
  TicketResponse,
  TicketStatus,
  TicketTracker,
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
}

function isOverdue(dueDate: string | null, status: TicketStatus): boolean {
  if (dueDate === null) return false
  if (status === 'resolved' || status === 'closed') return false
  return dueDate < new Date().toISOString().slice(0, 10)
}

/** 製品グループ型 */
interface ProductGroup {
  product: ProductResponse
  /** parent_id === null のチケット（ルートチケット） */
  rootTickets: TicketResponse[]
  /** 親チケット ID → 子チケット一覧 */
  childrenMap: Map<number, TicketResponse[]>
  /** グループ内の全チケット数（ヘッダー件数表示用） */
  totalCount: number
}

// ---- 製品グループヘッダー行 --------------------------------------------------

interface ProductGroupHeaderProps {
  group: ProductGroup
  collapsed: boolean
  onToggle: () => void
}

function ProductGroupHeader({ group, collapsed, onToggle }: ProductGroupHeaderProps) {
  return (
    <TableRow
      onClick={onToggle}
      sx={{
        backgroundColor: 'grey.50',
        cursor: 'pointer',
        '&:hover': { backgroundColor: 'grey.100' },
        borderTop: '2px solid',
        borderColor: 'divider',
      }}
    >
      <TableCell colSpan={COL_COUNT} sx={{ py: 0.75, px: 1 }}>
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
      </TableCell>
    </TableRow>
  )
}

// ---- チケット行 -----------------------------------------------------------

interface TicketRowProps {
  ticket: TicketResponse
  /** root: 製品直下チケット, child: 子チケット（インデント深め） */
  depth?: 'root' | 'child'
  hasChildren?: boolean
  childrenCollapsed?: boolean
  onToggle?: () => void
}

function TicketRow({ ticket, depth = 'root', hasChildren = false, childrenCollapsed = false, onToggle }: TicketRowProps) {
  const isChild = depth === 'child'
  // インデント: 子=8, 親（子あり）=2, ルート（子なし）=5
  const idCellPl = isChild ? 8 : hasChildren ? 2 : 5
  return (
    <TableRow
      hover
      sx={{ opacity: ['resolved', 'closed', 'rejected'].includes(ticket.status) ? 0.6 : 1 }}
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
            color={isChild ? 'text.secondary' : 'primary'}
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
              pl: isChild ? 2 : 0,
            }}
          >
            {ticket.subject}
          </Typography>
        </Tooltip>
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
        <Typography variant="body2" color="text.secondary" noWrap>
          {ticket.updated_at.slice(0, 10)}
        </Typography>
      </TableCell>
    </TableRow>
  )
}

// ---- ページ本体 -------------------------------------------------------------

// ---- フィルターパネル --------------------------------------------------------

interface FilterPanelProps {
  filter: TicketListQuery
  onChange: (v: TicketListQuery) => void
}

function FilterPanel({ filter, onChange }: FilterPanelProps) {
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
    </Paper>
  )
}

export default function SCR001_TicketListPage() {
  const [filter, setFilter] = useState<TicketListQuery>({ page: 1, page_size: 25 })
  /** 選択中のタブ値。ALL_PROJECTS_TAB または project_id (number) */
  const [activeProjectTab, setActiveProjectTab] = useState<string | number>(ALL_PROJECTS_TAB)
  /** 折りたたまれている製品 ID のセット */
  const [collapsedProducts, setCollapsedProducts] = useState<Set<number>>(new Set())
  /** 折りたたまれている親チケット ID のセット（デフォルト: 展開） */
  const [collapsedParentTickets, setCollapsedParentTickets] = useState<Set<number>>(new Set())

  const { data: projectsData } = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.getList(),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: [...QUERY_KEY, filter],
    queryFn: () => ticketsApi.getList(filter),
    select: (res) => res.data,
  })

  /** チケットを製品 ID でグループ化し、各グループ内を親子に分離する。
   * parent_id が同グループ内に存在しないチケットは root として扱う（データ不整合の吸収）。
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
    // 第2パス: グループ内で root / child に分類
    return Array.from(productMap.values()).map(({ product, allTickets }) => {
      const ticketIds = new Set(allTickets.map((t) => t.id))
      const rootTickets: TicketResponse[] = []
      const childrenMap = new Map<number, TicketResponse[]>()
      for (const ticket of allTickets) {
        // parent_id が null か、同グループ内に親が存在しない場合は root 扱い
        if (ticket.parent_id === null || !ticketIds.has(ticket.parent_id)) {
          rootTickets.push(ticket)
        } else {
          const siblings = childrenMap.get(ticket.parent_id) ?? []
          siblings.push(ticket)
          childrenMap.set(ticket.parent_id, siblings)
        }
      }
      return { product, rootTickets, childrenMap, totalCount: allTickets.length }
    })
  }, [data?.items])

  function toggleProduct(productId: number) {
    setCollapsedProducts((prev) => {
      const next = new Set(prev)
      if (next.has(productId)) next.delete(productId)
      else next.add(productId)
      return next
    })
  }

  function toggleParentTicket(ticketId: number) {
    setCollapsedParentTickets((prev) => {
      const next = new Set(prev)
      if (next.has(ticketId)) next.delete(ticketId)
      else next.add(ticketId)
      return next
    })
  }

  /** プロジェクトタブ切り替え。project_id フィルタとページをリセットする。 */
  function handleProjectTabChange(_: React.SyntheticEvent, value: string | number) {
    setActiveProjectTab(value)
    setCollapsedProducts(new Set())
    setCollapsedParentTickets(new Set())
    setFilter((prev) => ({
      ...prev,
      project_id: value === ALL_PROJECTS_TAB ? null : (value as number),
      page: 1,
    }))
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h1">チケット</Typography>
        {data && (
          <Typography variant="body2" color="text.secondary">{data.total} 件</Typography>
        )}
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
        <FilterPanel filter={filter} onChange={setFilter} />
      </Box>
      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>チケット一覧の読み込みに失敗しました。</Alert>
      )}
      <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
        {isLoading && <LinearProgress />}
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
              {isLoading
                ? /* ローディング中: スケルトン */
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: COL_COUNT }).map((__, j) => (
                      <TableCell key={j}><Skeleton variant="text" /></TableCell>
                    ))}
                  </TableRow>
                ))
                : productGroups.length > 0
                  ? /* 製品グループ別ツリー表示 */
                  productGroups.flatMap((group) => {
                    const groupCollapsed = collapsedProducts.has(group.product.id)
                    return [
                      <ProductGroupHeader
                        key={`group-${group.product.id}`}
                        group={group}
                        collapsed={groupCollapsed}
                        onToggle={() => toggleProduct(group.product.id)}
                      />,
                      ...(!groupCollapsed
                        ? group.rootTickets.flatMap((ticket) => {
                          const children = group.childrenMap.get(ticket.id) ?? []
                          const hasChildren = children.length > 0
                          const parentCollapsed = collapsedParentTickets.has(ticket.id)
                          return [
                            <TicketRow
                              key={ticket.id}
                              ticket={ticket}
                              depth="root"
                              hasChildren={hasChildren}
                              childrenCollapsed={parentCollapsed}
                              onToggle={() => toggleParentTicket(ticket.id)}
                            />,
                            ...(hasChildren && !parentCollapsed
                              ? children.map((child) => (
                                <TicketRow
                                  key={child.id}
                                  ticket={child}
                                  depth="child"
                                />
                              ))
                              : []),
                          ]
                        })
                        : []),
                    ]
                  })
                  : /* 該当なし */
                  [
                    <TableRow key="empty">
                      <TableCell colSpan={COL_COUNT} align="center" sx={{ py: 4 }}>
                        <Typography variant="body2" color="text.secondary">
                          条件に一致するチケットはありません。
                        </Typography>
                      </TableCell>
                    </TableRow>,
                  ]}
            </TableBody>
          </Table>
        </TableContainer>
        {data && data.total_pages > 1 && (
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
      </Paper>
    </Box>
  )
}
