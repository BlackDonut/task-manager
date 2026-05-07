import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Alert, Box, Chip, FormControl, InputLabel, MenuItem, Paper, Select, Skeleton,
  Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Tooltip, Typography,
} from '@mui/material'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutlined'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked'
import BlockIcon from '@mui/icons-material/Block'
import RemoveIcon from '@mui/icons-material/Remove'
import { projectsApi, ticketsApi } from '../api/endpoints/apis'
import type { PhaseCell, PhaseState, ProjectItem } from '../api/endpoints/types'

const MATRIX_QUERY_KEY = ['tickets', 'phase-matrix'] as const
const PROJECTS_QUERY_KEY = ['projects', 'list'] as const

// ---- セル状態定義 ---------------------------------------------------------

interface StateMeta {
  label: string
  bgSx: string
  colorSx: string
  icon: React.ReactNode
  tooltip: string
}

const STATE_META: Record<PhaseState, StateMeta> = {
  completed: { label: '完了', bgSx: 'success.50', colorSx: 'success.dark', icon: <CheckCircleOutlineIcon fontSize="small" />, tooltip: 'resolved または closed' },
  overdue: { label: '遅延', bgSx: 'error.50', colorSx: 'error.dark', icon: <ErrorOutlineIcon fontSize="small" />, tooltip: '期限超過・未完了' },
  in_progress: { label: '進行中', bgSx: 'warning.50', colorSx: 'warning.dark', icon: <HourglassEmptyIcon fontSize="small" />, tooltip: '進行中（期限内）' },
  not_started: { label: '未着手', bgSx: 'grey.100', colorSx: 'text.primary', icon: <RadioButtonUncheckedIcon fontSize="small" />, tooltip: '未着手' },
  rejected: { label: '却下', bgSx: 'grey.200', colorSx: 'text.secondary', icon: <BlockIcon fontSize="small" />, tooltip: '却下' },
  none: { label: '-', bgSx: 'grey.50', colorSx: 'text.disabled', icon: <RemoveIcon fontSize="small" />, tooltip: 'フェーズチケットなし' },
}

// ---- サブコンポーネント ---------------------------------------------------

interface PhaseCellChipProps { cell: PhaseCell }

function PhaseCellChip({ cell }: PhaseCellChipProps) {
  const meta = STATE_META[cell.state]
  const lines = [meta.tooltip, cell.due_date ? `期日: ${cell.due_date}` : null, cell.ticket_id ? `#${cell.ticket_id}` : null]
    .filter(Boolean).join(' / ')
  return (
    <Tooltip title={lines} placement="top">
      <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.5, borderRadius: 1, bgcolor: meta.bgSx, color: meta.colorSx, fontSize: '0.75rem', fontWeight: 500, whiteSpace: 'nowrap' }} role="img" aria-label={meta.label}>
        {meta.icon}{meta.label}
      </Box>
    </Tooltip>
  )
}

function Legend() {
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
      {(Object.keys(STATE_META) as PhaseState[]).map((state) => {
        const meta = STATE_META[state]
        return <Chip key={state} size="small" label={meta.label} sx={{ bgcolor: meta.bgSx, color: meta.colorSx, fontWeight: 500, fontSize: '0.7rem' }} />
      })}
    </Stack>
  )
}

// ---- メインコンポーネント --------------------------------------------------

export default function SCR005_PhaseMatrixPage() {
  const [projectId, setProjectId] = useState<number | ''>('')

  const { data: projectsData } = useQuery({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: () => projectsApi.getList().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })
  const projects: ProjectItem[] = projectsData?.items ?? []

  const { data: matrixData, isLoading, isError } = useQuery({
    queryKey: [...MATRIX_QUERY_KEY, projectId],
    queryFn: () => ticketsApi.getPhaseMatrix(projectId !== '' ? { project_id: projectId } : undefined).then((r) => r.data),
    staleTime: 60 * 1000,
  })

  const phases = matrixData?.phases ?? []
  const rows = matrixData?.rows ?? []

  const completedProductCount = rows.filter((row) => {
    const hasPhases = row.cells.some((c) => c.state !== 'none')
    return hasPhases && row.cells.every((c) => c.state === 'completed' || c.state === 'rejected' || c.state === 'none')
  }).length

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 'bold' }} gutterBottom>フェーズ進捗マトリクス</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>製品ごとに全フェーズの完了状態を確認します。</Typography>

      <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap', mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>プロジェクト</InputLabel>
          <Select label="プロジェクト" value={projectId} onChange={(e) => setProjectId(e.target.value as number | '')}>
            <MenuItem value="">すべて</MenuItem>
            {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </Select>
        </FormControl>
        <Legend />
      </Stack>

      {!isLoading && !isError && rows.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {rows.length} 製品中{' '}
          <Box component="span" sx={{ fontWeight: 'bold', color: 'success.main' }}>{completedProductCount} 製品</Box>{' '}
          が全フェーズ完了
        </Typography>
      )}

      {isError && <Alert severity="error" sx={{ mb: 2 }}>データの読み込みに失敗しました。</Alert>}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 160, bgcolor: 'grey.50', borderRight: 1, borderColor: 'divider' }}>製品</TableCell>
              {isLoading
                ? Array.from({ length: 4 }).map((_, i) => <TableCell key={i} sx={{ bgcolor: 'grey.50' }}><Skeleton width={80} /></TableCell>)
                : phases.map((phase) => <TableCell key={phase} align="center" sx={{ fontWeight: 'bold', bgcolor: 'grey.50', whiteSpace: 'nowrap', fontSize: '0.75rem' }}>{phase}</TableCell>)
              }
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell sx={{ borderRight: 1, borderColor: 'divider' }}><Skeleton width={120} /></TableCell>
                    {Array.from({ length: 4 }).map((_, j) => <TableCell key={j} align="center"><Skeleton width={64} height={28} sx={{ mx: 'auto' }} /></TableCell>)}
                  </TableRow>
                ))
              : rows.map((row) => {
                  const hasPhases = row.cells.some((c) => c.state !== 'none')
                  const allDone = hasPhases && row.cells.every((c) => c.state === 'completed' || c.state === 'rejected' || c.state === 'none')
                  return (
                    <TableRow key={row.product.id} sx={{ bgcolor: allDone ? 'success.50' : undefined }}>
                      <TableCell sx={{ fontWeight: 500, borderRight: 1, borderColor: 'divider', whiteSpace: 'nowrap' }}>
                        {row.product.name}
                        {allDone && <CheckCircleOutlineIcon fontSize="inherit" sx={{ ml: 0.5, color: 'success.main', verticalAlign: 'middle' }} />}
                      </TableCell>
                      {row.cells.map((cell) => <TableCell key={cell.phase_subject} align="center"><PhaseCellChip cell={cell} /></TableCell>)}
                    </TableRow>
                  )
                })
            }
            {!isLoading && rows.length === 0 && !isError && (
              <TableRow>
                <TableCell colSpan={phases.length + 1} align="center" sx={{ py: 4, color: 'text.secondary' }}>表示するデータがありません</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
