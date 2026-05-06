/**
 * アプリ共通レイアウト。
 * グローバルナビゲーションバーとページコンテンツ領域を提供する。
 */
import { AppBar, Box, Tab, Tabs, Toolbar, Typography } from '@mui/material'
import { useLocation, useNavigate } from 'react-router-dom'

/** ナビゲーション定義。追加時はここにエントリを足す。 */
const NAV_ITEMS = [
  { label: 'チケット一覧', path: '/tickets' },
  { label: 'ガントチャート', path: '/gantt' },
] as const

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()

  /** 現在のパスに対応するタブのインデックスを返す。未一致は false（タブ非選択）。 */
  const currentTab =
    NAV_ITEMS.findIndex((item) => location.pathname.startsWith(item.path))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" elevation={1} sx={{ bgcolor: 'primary.main' }}>
        <Toolbar variant="dense" sx={{ gap: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'inherit', whiteSpace: 'nowrap' }}>
            タスク管理
          </Typography>
          <Tabs
            value={currentTab === -1 ? false : currentTab}
            onChange={(_, idx: number) => navigate(NAV_ITEMS[idx].path)}
            textColor="inherit"
            slotProps={{ indicator: { style: { backgroundColor: '#fff' } } }}
            sx={{ minHeight: 48 }}
          >
            {NAV_ITEMS.map((item) => (
              <Tab
                key={item.path}
                label={item.label}
                sx={{ minHeight: 48, color: 'rgba(255,255,255,0.75)', '&.Mui-selected': { color: '#fff' } }}
              />
            ))}
          </Tabs>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flex: 1 }}>
        {children}
      </Box>
    </Box>
  )
}
