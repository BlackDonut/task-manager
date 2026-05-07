/**
 * プロジェクト選択画面（SCR-P000）。
 * アプリ起動時のランディングページ。プロジェクトカードを一覧表示し、
 * 選択したプロジェクトのチケット一覧・ガントチャート・リスク管理へ遷移する。
 *
 * 複数プロジェクトが並行稼働する業務を想定し、「どのプロジェクトを確認するか」を
 * 最初に選択させることで操作ミス・見落としを防ぐ。
 */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Divider,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import AssignmentIcon from '@mui/icons-material/Assignment'
import TimelineIcon from '@mui/icons-material/Timeline'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import { projectsApi } from '../api/endpoints/apis'
import type { ProjectItem } from '../api/endpoints/types'

const PROJECTS_QUERY_KEY = ['projects', 'list'] as const

/** プロジェクト 1 件のカードコンポーネント。 */
function ProjectCard({ project }: { project: ProjectItem }) {
  const navigate = useNavigate()

  return (
    <Card
      variant="outlined"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 4 },
      }}
    >
      <CardContent sx={{ flex: 1 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', mb: 1 }}>
          <FolderOpenIcon sx={{ color: 'primary.main', mt: 0.25 }} />
          <Typography variant="h6" sx={{ fontWeight: 'bold', lineHeight: 1.3 }}>
            {project.name}
          </Typography>
        </Stack>
      </CardContent>
      <Divider />
      <CardActions sx={{ p: 1.5, flexWrap: 'wrap', gap: 1 }}>
        <Button
          size="small"
          variant="contained"
          startIcon={<AssignmentIcon />}
          onClick={() => navigate(`/tickets?project_id=${project.id}`)}
        >
          チケット一覧
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<TimelineIcon />}
          onClick={() => navigate(`/gantt?project_id=${project.id}`)}
        >
          ガントチャート
        </Button>
        <Button
          size="small"
          variant="outlined"
          color="warning"
          startIcon={<WarningAmberIcon />}
          onClick={() => navigate(`/risk?project_id=${project.id}`)}
        >
          リスク管理
        </Button>
      </CardActions>
    </Card>
  )
}

/** プロジェクト選択画面本体。 */
export default function SCR000_ProjectSelectPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: PROJECTS_QUERY_KEY,
    queryFn: () => projectsApi.getList().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <Box sx={{ p: 4, maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 0.5 }}>
          プロジェクト一覧
        </Typography>
        <Typography variant="body1" color="text.secondary">
          確認するプロジェクトを選択してください。
        </Typography>
      </Box>

      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          プロジェクト一覧の読み込みに失敗しました。再読み込みしてください。
        </Alert>
      )}

      {/* プロジェクトカードグリッド */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)',
          },
          gap: 3,
        }}
      >
        {isPending
          ? /* ローディング: スケルトンカード */
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height={160} sx={{ borderRadius: 1 }} />
          ))
          : data?.items.map((project: ProjectItem) => (
            <ProjectCard key={project.id} project={project} />
          ))}

        {!isPending && data?.items.length === 0 && (
          <Box sx={{ gridColumn: '1 / -1', textAlign: 'center', py: 8 }}>
            <Typography color="text.secondary">
              プロジェクトが登録されていません。
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  )
}
