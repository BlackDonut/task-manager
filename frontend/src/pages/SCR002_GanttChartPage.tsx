/**
 * ガントチャートページ（SCR-G001）。
 * チケットをガントチャート形式で表示する。製品ヘッダーの下にフェーズ行を配置する。
 *
 * gantt-task-react v0.3.x の既知挙動と対策:
 *   1. 内部 sort(sortTasks) が displayOrder 昇順でソートする。
 *      displayOrder 未設定 = Number.MAX_VALUE 扱いで安定性が保証されないため、
 *      全タスクに連番 displayOrder を付与して製品→フェーズ順を確定させる。
 *   2. 内部 useEffect → setBarTasks のためマウント直後 1 フレームだけバーが空になる。
 *      ganttVisible + Skeleton オーバーレイで blank フレームを隠す。
 *   3. overflowY: auto コンテナと競合すると縦スクロールが先頭に戻る。
 *      Paper に overflowY: hidden を設定する。
 */
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Gantt, type Task, ViewMode } from 'gantt-task-react'
import 'gantt-task-react/dist/index.css'
import {
  Alert,
  Box,
  ButtonGroup,
  Button,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  LinearProgress,
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
} from '../api/endpoints/types'

const GANTT_QUERY_KEY = ['tickets', 'gantt'] as const
const PROJECTS_QUERY_KEY = ['projects', 'list'] as const

/**
 * gantt-task-react のデフォルト行高 (px)。
 * ganttHeight をタスク行数 × ROW_HEIGHT で動的計算することで
 * 内部縦スクロールコンテナを不要にし、スクロール先頭リセットバグを解消する。
 */
const ROW_HEIGHT = 50
/** ganttHeight の最小値 (px)。タスクゼロ時のローディングスケルトン高さとも兼用。 */
const GANTT_HEIGHT_MIN = 300

const STATUS_LABEL: Record<TicketStatus, string> = {
  new: '新規',
  in_progress: '進行中',
  resolved: '解決済み',
  closed: '終了',
  rejected: '却下',
}

/** ステータスに対応する MUI Chip カラー。 */
const STATUS_CHIP_COLOR: Record<TicketStatus, 'default' | 'primary' | 'warning' | 'success' | 'error'> = {
  new: 'primary',
  in_progress: 'warning',
  resolved: 'success',
  closed: 'default',
  rejected: 'error',
}

const VIEW_MODES: [ViewMode, string][] = [
  [ViewMode.Day, '日'],
  [ViewMode.Week, '週'],
  [ViewMode.Month, '月'],
]

/** 製品 ID に対応するガントバー色セット（循環割り当て）。rgba バリアントを事前定義して文字列計算を省く。 */
const BAR_PALETTE = [
  { base: 'rgb(59,130,246)', taskBg: 'rgba(59,130,246,0.35)', taskSel: 'rgba(59,130,246,0.55)', projBg: 'rgba(59,130,246,0.15)', projSel: 'rgba(59,130,246,0.30)' },
  { base: 'rgb(139,92,246)', taskBg: 'rgba(139,92,246,0.35)', taskSel: 'rgba(139,92,246,0.55)', projBg: 'rgba(139,92,246,0.15)', projSel: 'rgba(139,92,246,0.30)' },
  { base: 'rgb(16,185,129)', taskBg: 'rgba(16,185,129,0.35)', taskSel: 'rgba(16,185,129,0.55)', projBg: 'rgba(16,185,129,0.15)', projSel: 'rgba(16,185,129,0.30)' },
  { base: 'rgb(245,158,11)', taskBg: 'rgba(245,158,11,0.35)', taskSel: 'rgba(245,158,11,0.55)', projBg: 'rgba(245,158,11,0.15)', projSel: 'rgba(245,158,11,0.30)' },
  { base: 'rgb(239,68,68)', taskBg: 'rgba(239,68,68,0.35)', taskSel: 'rgba(239,68,68,0.55)', projBg: 'rgba(239,68,68,0.15)', projSel: 'rgba(239,68,68,0.30)' },
  { base: 'rgb(6,182,212)', taskBg: 'rgba(6,182,212,0.35)', taskSel: 'rgba(6,182,212,0.55)', projBg: 'rgba(6,182,212,0.15)', projSel: 'rgba(6,182,212,0.30)' },
] as const

function getPalette(productId: number) {
  return BAR_PALETTE[productId % BAR_PALETTE.length]
}

/** YYYY-MM-DD 文字列をローカル日付の Date に変換する。 */
function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const DAY_MS = 24 * 60 * 60 * 1000

/**
 * GanttTicketResponse[] を「製品ヘッダー → フェーズ行」の Task[] に変換する。
 *
 * ● tracker==='phase' のチケットのみを行として描画する。
 * ● 製品行 (type:'project') の直後にその製品のフェーズを配置する（ライブラリ要件）。
 * ● due_date 未設定は start + 7 日、end <= start は start + 1 日に補正する。
 * ● predecessor_ids がある場合、gantt-task-react の dependencies フィールドで矢印表示する。
 *   フィルタ後に対応フェーズが存在しない ID は除外して描画エラーを防ぐ。
 *
 * @param collapsedGroupIds - 折りたたみ中のグループ ID セット（"product-{id}" 形式）
 */
function toGanttTasksByProductPhase(
  tickets: GanttTicketResponse[],
  collapsedGroupIds: ReadonlySet<string>,
): Task[] {
  // フィルタ後に存在するフェーズ ID セット（存在しない predecessor_id を除外するために使用）
  const phaseTickets = tickets.filter((t) => t.tracker === 'phase')
  const allPhaseIds = new Set(phaseTickets.map((t) => t.id))

  // 製品ごとのメタ情報と所属フェーズを収集する（Map で挿入順を保持）
  const productMeta = new Map<
    number,
    { name: string; minStart: Date; maxEnd: Date; phases: GanttTicketResponse[] }
  >()

  for (const phase of phaseTickets) {
    const start = parseLocalDate(phase.start_date)
    const rawEnd = phase.due_date
      ? parseLocalDate(phase.due_date)
      : new Date(start.getTime() + 7 * DAY_MS)
    const end = rawEnd <= start ? new Date(start.getTime() + DAY_MS) : rawEnd

    const prev = productMeta.get(phase.product.id)
    if (!prev) {
      productMeta.set(phase.product.id, { name: phase.product.name, minStart: start, maxEnd: end, phases: [phase] })
    } else {
      if (start < prev.minStart) prev.minStart = start
      if (end > prev.maxEnd) prev.maxEnd = end
      prev.phases.push(phase)
    }
  }

  const tasks: Task[] = []
  // displayOrder を 1 始まりの連番で付与して sortTasks による並び替えを確定させる。
  // gantt-task-react の sortTasks は `displayOrder || Number.MAX_VALUE` で評価するため、
  // 0（falsy）を設定すると Number.MAX_VALUE 扱いになり最後尾に移動してしまう（グループ崩れ）。
  // 1 始まりにすることで全タスクが正しい順序でソートされる。
  let displayOrder = 1
  let paletteIdx = 0

  for (const [pid, meta] of productMeta.entries()) {
    const p = getPalette(paletteIdx++)
    const productTaskId = `product-${pid}`

    // 製品ヘッダー行（type: 'project'）
    tasks.push({
      id: productTaskId,
      name: `[${meta.name}]`,
      start: meta.minStart,
      end: meta.maxEnd,
      progress: 0,
      type: 'project',
      hideChildren: collapsedGroupIds.has(productTaskId),
      displayOrder: displayOrder++,
      styles: {
        backgroundColor: p.projBg,
        backgroundSelectedColor: p.projSel,
        progressColor: p.base,
        progressSelectedColor: p.base,
      },
    })

    // 製品行の直後にフェーズを連番で配置する（gantt-task-react の配列順要件）
    for (const phase of meta.phases) {
      const start = parseLocalDate(phase.start_date)
      const rawEnd = phase.due_date
        ? parseLocalDate(phase.due_date)
        : new Date(start.getTime() + 7 * DAY_MS)
      const end = rawEnd <= start ? new Date(start.getTime() + DAY_MS) : rawEnd

      // 先行関係: フィルタ後に存在するフェーズ ID のみ dependencies に含める（描画エラー防止）
      const dependencies = phase.predecessor_ids
        .filter((id) => allPhaseIds.has(id))
        .map((id) => `phase-${id}`)

      tasks.push({
        id: `phase-${phase.id}`,
        name: phase.subject,
        start,
        end,
        progress: phase.done_ratio,
        type: 'task',
        project: productTaskId,
        displayOrder: displayOrder++,
        dependencies: dependencies.length > 0 ? dependencies : undefined,
        styles: {
          backgroundColor: p.taskBg,
          backgroundSelectedColor: p.taskSel,
          progressColor: p.base,
          progressSelectedColor: p.base,
        },
      })
    }
  }

  return tasks
}


export default function SCR002_GanttChartPage() {
  const [searchParams] = useSearchParams()

  const [projectId, setProjectId] = useState<number | ''>(() => {
    const pid = searchParams.get('project_id')
    return pid ? parseInt(pid, 10) : ''
  })
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('')
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Week)
  const [collapsedGroupIds, setCollapsedGroupIds] = useState<ReadonlySet<string>>(new Set())
  /** フェーズ行クリック時に残タスクパネルへ表示するフェーズチケット ID。 */
  const [selectedPhaseId, setSelectedPhaseId] = useState<number | null>(null)

  /**
   * gantt-task-react は内部 useEffect で barTasks を設定するため、
   * マウント直後の 1 フレームだけバーが描画されない（blank フレーム問題）。
   *
   * 【白画面バグの原因と対策】
   * ganttVisible: false→true 変化時、Paper の opacity フェードイン（0→1, 150ms）中に
   * Skeleton が先に unmount されると白背景が透けて「真っ白画面」になる。
   * skeletonVisible を独立させ、Paper の onTransitionEnd（フェード完了後）に
   * Skeleton を unmount することで白背景の露出を防ぐ。
   *
   * 状態遷移:
   *   1. data 到着 → ganttVisible=false, skeletonVisible=true (Skeleton 表示)
   *   2. 1 rAF 後  → ganttVisible=true (Paper がフェードイン開始)
   *   3. 150ms 後  → onTransitionEnd → skeletonVisible=false (Skeleton が消える)
   */
  const [ganttVisible, setGanttVisible] = useState(false)
  /**
   * Skeleton の表示フラグ。ganttVisible=true になった後も opacity トランジション完了まで
   * true を維持し、onTransitionEnd で false にする。
   */
  const [skeletonVisible, setSkeletonVisible] = useState(false)

  const { data: projectsData } = useQuery({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: () => projectsApi.getList().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const ganttQuery: GanttTicketQuery = useMemo(
    () => ({
      ...(projectId !== '' ? { project_id: projectId } : {}),
      ...(statusFilter !== '' ? { status: statusFilter } : {}),
    }),
    [projectId, statusFilter],
  )

  const { data, isPending, isError } = useQuery({
    queryKey: [...GANTT_QUERY_KEY, ganttQuery],
    queryFn: () => ticketsApi.getGanttList(ganttQuery).then((r) => r.data),
    staleTime: 30 * 1000,
  })

  // フィルタ変更時に折りたたみ状態・選択フェーズをリセットする（render-time setState パターン）
  const [prevQuery, setPrevQuery] = useState(ganttQuery)
  if (ganttQuery !== prevQuery) {
    setPrevQuery(ganttQuery)
    setCollapsedGroupIds(new Set())
    setSelectedPhaseId(null)
  }

  // data が変化したとき（API レスポンス到着時）に ganttVisible をリセットし、
  // gantt-task-react の内部 useEffect 完了後（1 rAF）に表示する。
  // collapse 操作では data が変化しないため Skeleton は出ない。
  useEffect(() => {
    if (!data?.items?.length) {
      setGanttVisible(false)
      setSkeletonVisible(false)
      return
    }
    // Skeleton を先に表示してから Gantt をマウント（blank フレームを隠す）
    setGanttVisible(false)
    setSkeletonVisible(true)
    const rafId = requestAnimationFrame(() => setGanttVisible(true))
    // Skeleton の消去は onTransitionEnd（Paper フェード完了後）に委ねるため RAF では行わない
    return () => cancelAnimationFrame(rafId)
  }, [data])

  /** 選択中のフェーズチケット。 */
  const selectedPhase = useMemo(
    () =>
      selectedPhaseId !== null
        ? (data?.items.find((t) => t.id === selectedPhaseId && t.tracker === 'phase') ?? null)
        : null,
    [selectedPhaseId, data],
  )

  /**
   * 選択フェーズに属する未完了タスク一覧。
   * closed / rejected / resolved は「完了済み」として除外する。
   */
  const remainingTasks = useMemo(
    () =>
      selectedPhaseId !== null
        ? (data?.items.filter(
          (t) =>
            t.parent_id === selectedPhaseId &&
            t.tracker !== 'phase' &&
            t.status !== 'closed' &&
            t.status !== 'rejected' &&
            t.status !== 'resolved',
        ) ?? [])
        : [],
    [selectedPhaseId, data],
  )

  const ganttTasks = useMemo(
    () => {
      if (!data?.items?.length) return []
      return toGanttTasksByProductPhase(data.items, collapsedGroupIds)
    },
    [data, collapsedGroupIds],
  )

  const columnWidth = viewMode === ViewMode.Day ? 60 : viewMode === ViewMode.Week ? 150 : 250
  const hasTickets = Boolean(data?.items?.length)

  /**
   * タスク行数 × ROW_HEIGHT でガント高さを動的計算する。
   * ganttHeight がコンテンツ高さ以上になるため内部縦スクロールが発生せず、
   * スクロール同期ループ（先頭リセット）バグを根本的に回避できる。
   * ページ自体のスクロールで全行を閲覧可能。
   */
  const ganttHeight = Math.max(GANTT_HEIGHT_MIN, ganttTasks.length * ROW_HEIGHT)

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
      ) : !hasTickets ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">表示するチケットがありません。フィルターを変更してください。</Typography>
        </Paper>
      ) : (
        <Box sx={{ position: 'relative' }}>
          {/* Skeleton は ganttVisible=false の間 + opacity トランジション完了まで維持する。
              onTransitionEnd で skeletonVisible=false にすることで白背景の透過を防ぐ。 */}
          {skeletonVisible && (
            <Skeleton
              variant="rectangular"
              height={ganttHeight + 50}
              sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1, borderRadius: 1 }}
            />
          )}
          <Paper
            onTransitionEnd={() => {
              // opacity フェードイン完了後に Skeleton を unmount して描画コストを削減する
              if (ganttVisible) setSkeletonVisible(false)
            }}
            sx={{
              p: 1,
              overflowX: 'auto',
              overflowY: 'hidden',
              opacity: ganttVisible ? 1 : 0,
              transition: 'opacity 0.15s ease-in',
            }}
          >
            <Gantt
              tasks={ganttTasks}
              viewMode={viewMode}
              locale="ja-JP"
              ganttHeight={ganttHeight}
              listCellWidth="220px"
              columnWidth={columnWidth}
              onSelect={(task, isSelected) => {
                // フェーズバー選択で残タスクパネルを表示する
                if (!isSelected) {
                  setSelectedPhaseId(null)
                  return
                }
                if (!task.id.startsWith('phase-')) return
                const phaseId = parseInt(task.id.replace('phase-', ''), 10)
                setSelectedPhaseId(isNaN(phaseId) ? null : phaseId)
              }}
              onExpanderClick={(task) => {
                if (task.type !== 'project') return
                setCollapsedGroupIds((prev) => {
                  const next = new Set(prev)
                  if (task.hideChildren) next.add(task.id)
                  else next.delete(task.id)
                  return next
                })
              }}
            />
          </Paper>
        </Box>
      )}

      {data != null && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {data.total} 件表示（最大 500 件）
        </Typography>
      )}

      {/* フェーズバーをクリックすると未完了タスク一覧を表示する */}
      {selectedPhase !== null && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {selectedPhase.subject}　残タスク（{remainingTasks.length} 件）
            </Typography>
            <Button size="small" variant="outlined" onClick={() => setSelectedPhaseId(null)}>
              閉じる
            </Button>
          </Box>
          <Divider sx={{ mb: 1.5 }} />
          {remainingTasks.length === 0 ? (
            <Typography color="text.secondary">このフェーズの未完了タスクはありません。</Typography>
          ) : (
            <Stack spacing={1}>
              {remainingTasks.map((t) => (
                <Box
                  key={t.id}
                  sx={{
                    p: 1.5,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                  }}
                >
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      #{t.id}　{t.subject}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                      <Chip
                        label={STATUS_LABEL[t.status]}
                        size="small"
                        color={STATUS_CHIP_COLOR[t.status]}
                        variant="outlined"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {t.assignee?.display_name ?? '未割当'}
                      </Typography>
                      {t.due_date && (
                        <Typography variant="caption" color="text.secondary">
                          期日: {t.due_date}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  {/* 進捗バー */}
                  <Box sx={{ width: 130, flexShrink: 0 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'right', mb: 0.5 }}>
                      {t.done_ratio}%
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={t.done_ratio}
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                  </Box>
                </Box>
              ))}
            </Stack>
          )}
        </Paper>
      )}
    </Box>
  )
}

