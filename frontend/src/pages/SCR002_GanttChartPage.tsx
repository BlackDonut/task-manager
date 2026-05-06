/**
 * ガントチャートページ（SCR-G001）。
 * チケットをガントチャート形式で表示する。製品単位でグループ化する。
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Gantt, type Task, ViewMode } from 'gantt-task-react'
import 'gantt-task-react/dist/index.css'
import {
  Alert,
  Box,
  ButtonGroup,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { projectsApi, ticketsApi } from '../api/endpoints/apis'
import type {
  GanttTicketResponse,
  GanttTicketQuery,
  ProjectItem,
  TicketStatus,
  TicketTracker,
} from '../api/endpoints/types'

const GANTT_QUERY_KEY = ['tickets', 'gantt'] as const
const PROJECTS_QUERY_KEY = ['projects', 'list'] as const

const STATUS_LABEL: Record<TicketStatus, string> = {
  new: '新規',
  in_progress: '進行中',
  resolved: '解決済み',
  closed: '終了',
  rejected: '却下',
}

const TRACKER_LABEL: Record<TicketTracker, string> = {
  bug: 'バグ',
  feature: '機能',
  support: 'サポート',
  task: 'タスク',
}

const VIEW_MODES: [ViewMode, string][] = [
  [ViewMode.Day, '日'],
  [ViewMode.Week, '週'],
  [ViewMode.Month, '月'],
]

/** 製品 ID に対応するガントバー色（循環割り当て）。 */
const BAR_PALETTE = [
  'rgb(59,130,246)',
  'rgb(139,92,246)',
  'rgb(16,185,129)',
  'rgb(245,158,11)',
  'rgb(239,68,68)',
  'rgb(6,182,212)',
] as const

function getBarColor(productId: number): string {
  return BAR_PALETTE[productId % BAR_PALETTE.length]
}

/** YYYY-MM-DD 文字列をローカル日付の Date に変換する。 */
function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const DAY_MILLISECONDS = 24 * 60 * 60 * 1000

/**
 * GanttTicketResponse[] を gantt-task-react の Task[] に変換する。
 * 製品ごとに "project" タイプのグループバーを先頭に追加する。
 * due_date 未設定は start + 7 日を end として扱う。
 * end <= start の場合は start + 1 日に補正する。
 */
function toGanttTasks(tickets: GanttTicketResponse[]): Task[] {
  const productMeta = new Map<number, { name: string; minStart: Date; maxEnd: Date }>()

  for (const t of tickets) {
    const start = parseLocalDate(t.start_date)
    const rawEnd = t.due_date
      ? parseLocalDate(t.due_date)
      : new Date(start.getTime() + 7 * DAY_MILLISECONDS)
    const safeEnd = rawEnd <= start ? new Date(start.getTime() + DAY_MILLISECONDS) : rawEnd

    const prev = productMeta.get(t.product.id)
    if (!prev) {
      productMeta.set(t.product.id, { name: t.product.name, minStart: start, maxEnd: safeEnd })
    } else {
      if (start < prev.minStart) prev.minStart = start
      if (safeEnd > prev.maxEnd) prev.maxEnd = safeEnd
    }
  }

  const tasks: Task[] = []

  for (const [pid, meta] of productMeta.entries()) {
    const color = getBarColor(pid)
    const colorA = color.replace('rgb(', 'rgba(').replace(')', ', 0.2)')
    const colorB = color.replace('rgb(', 'rgba(').replace(')', ', 0.35)')
    tasks.push({
      id: `product-${pid}`,
      name: meta.name,
      start: meta.minStart,
      end: meta.maxEnd,
      progress: 0,
      type: 'project',
      hideChildren: false,
      styles: { backgroundColor: colorA, backgroundSelectedColor: colorB, progressColor: color, progressSelectedColor: color },
    })
  }

  for (const t of tickets) {
    const start = parseLocalDate(t.start_date)
    const rawEnd = t.due_date
      ? parseLocalDate(t.due_date)
      : new Date(start.getTime() + 7 * DAY_MILLISECONDS)
    const safeEnd = rawEnd <= start ? new Date(start.getTime() + DAY_MILLISECONDS) : rawEnd
    const color = getBarColor(t.product.id)
    const colorA = color.replace('rgb(', 'rgba(').replace(')', ', 0.35)')
    const colorB = color.replace('rgb(', 'rgba(').replace(')', ', 0.55)')
    tasks.push({
      id: `ticket-${t.id}`,
      name: `#${t.id} ${t.subject}`,
      start,
      end: safeEnd,
      progress: t.done_ratio,
      type: 'task',
      project: `product-${t.product.id}`,
      styles: { backgroundColor: colorA, backgroundSelectedColor: colorB, progressColor: color, progressSelectedColor: color },
    })
  }

  return tasks
}

export default function SCR002_GanttChartPage() {
  const [projectId, setProjectId] = useState<number | ''>('')
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('')
  const [trackerFilter, setTrackerFilter] = useState<TicketTracker | ''>('')
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Week)
  const [ganttTasks, setGanttTasks] = useState<Task[]>([])

  const { data: projectsData } = useQuery({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: () => projectsApi.getList().then((r) => r.data),
  })

  const ganttQuery: GanttTicketQuery = useMemo(
    () => ({
      ...(projectId !== '' ? { project_id: projectId } : {}),
      ...(statusFilter !== '' ? { status: statusFilter } : {}),
      ...(trackerFilter !== '' ? { tracker: trackerFilter } : {}),
    }),
    [projectId, statusFilter, trackerFilter],
  )

  const { data, isPending, isError } = useQuery({
    queryKey: [...GANTT_QUERY_KEY, ganttQuery],
    queryFn: () => ticketsApi.getGanttList(ganttQuery).then((r) => r.data),
  })

  useEffect(() => {
    setGanttTasks(data?.items?.length ? toGanttTasks(data.items) : [])
  }, [data])

  const columnWidth = viewMode === ViewMode.Day ? 60 : viewMode === ViewMode.Week ? 150 : 250

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 2 }}>ガントチャート</Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap' }} useFlexGap>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>プロジェクト</InputLabel>
            <Select value={projectId} label="プロジェクト" onChange={(e) => setProjectId(e.target.value as number | '')}>
              <MenuItem value="">すべて</MenuItem>
              {projectsData?.items.map((p: ProjectItem) => (
                <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>ステータス</InputLabel>
            <Select value={statusFilter} label="ステータス" onChange={(e) => setStatusFilter(e.target.value as TicketStatus | '')}>
              <MenuItem value="">すべて</MenuItem>
              {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
                <MenuItem key={s} value={s}>{STATUS_LABEL[s]}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 130 }}>
            <InputLabel>トラッカー</InputLabel>
            <Select value={trackerFilter} label="トラッカー" onChange={(e) => setTrackerFilter(e.target.value as TicketTracker | '')}>
              <MenuItem value="">すべて</MenuItem>
              {(Object.keys(TRACKER_LABEL) as TicketTracker[]).map((tr) => (
                <MenuItem key={tr} value={tr}>{TRACKER_LABEL[tr]}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <ButtonGroup size="small" variant="outlined">
            {VIEW_MODES.map(([mode, label]) => (
              <Button key={mode} onClick={() => setViewMode(mode)} variant={viewMode === mode ? 'contained' : 'outlined'}>
                {label}
              </Button>
            ))}
          </ButtonGroup>
        </Stack>
      </Paper>

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>データの取得に失敗しました。再読み込みしてください。</Alert>
      )}

      {isPending ? (
        <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 1 }} />
      ) : ganttTasks.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">表示するチケットがありません。フィルターを変更してください。</Typography>
        </Paper>
      ) : (
        <Paper sx={{ p: 1, overflow: 'auto' }}>
          <Gantt
            tasks={ganttTasks}
            viewMode={viewMode}
            locale="ja-JP"
            ganttHeight={Math.min(600, ganttTasks.length * 50 + 60)}
            listCellWidth="200px"
            columnWidth={columnWidth}
            onExpanderClick={(task) => setGanttTasks((prev) => prev.map((t) => (t.id === task.id ? task : t)))}
          />
        </Paper>
      )}

      {data != null && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {data.total} 件表示（最大 500 件）
        </Typography>
      )}
    </Box>
  )
}

