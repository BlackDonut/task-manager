/**
 * フロントエンドの簡易ホーム画面を表示する。
 * 仕様: README.md
 * 画面: SCR001
 * 業務制約: 実装途中の画面参照を避け、現存ソースのみで起動可能に保つ
 */
import { Box, List, ListItem, ListItemText, Paper, Stack, Typography } from '@mui/material'

const availableModules = [
  'FastAPI バックエンドとの接続基盤',
  'MUI テーマ設定',
  'Axios API クライアント',
  'WebSocket イベント型定義',
] as const

/**
 * アプリケーションのルート画面を描画する。
 */
export default function App() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 3,
        backgroundColor: 'background.default',
      }}
    >
      <Paper elevation={0} sx={{ width: '100%', maxWidth: 720, p: 4 }}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Typography variant="h1">Task Manager</Typography>
            <Typography variant="body1" color="text.secondary">
              現在のフロントエンドは、ワークスペース上に存在するソースのみで起動できる最小構成に揃えています。
            </Typography>
          </Stack>

          <Box>
            <Typography variant="h2" sx={{ mb: 1.5 }}>
              利用可能な構成要素
            </Typography>
            <List disablePadding>
              {availableModules.map((moduleName) => (
                <ListItem key={moduleName} disablePadding sx={{ py: 0.5 }}>
                  <ListItemText primary={moduleName} />
                </ListItem>
              ))}
            </List>
          </Box>

          <Box>
            <Typography variant="h2" sx={{ mb: 1.5 }}>
              次の確認ポイント
            </Typography>
            <Typography variant="body2" color="text.secondary">
              バックエンドの healthz と、依存パッケージ展開後のビルド確認を行うと、次の整合性確認に進めます。
            </Typography>
          </Box>
        </Stack>
      </Paper>
    </Box>
  )
}
