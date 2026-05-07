/**
 * アプリ共通レイアウト。
 * トグル可能なサイドバーナビゲーションとページコンテンツ領域を提供する。
 */
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import FolderIcon from '@mui/icons-material/Folder'
import ListAltIcon from '@mui/icons-material/ListAlt'
import BarChartIcon from '@mui/icons-material/BarChart'
import DashboardIcon from '@mui/icons-material/Dashboard'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import GridOnIcon from '@mui/icons-material/GridOn'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/** サイドバーの幅（px）。 */
const DRAWER_WIDTH = 220

/** ナビゲーション定義。追加時はここにエントリを足す。 */
const NAV_ITEMS = [
  { label: 'プロジェクト', path: '/', icon: <FolderIcon fontSize="small" /> },
  { label: 'チケット一覧', path: '/tickets', icon: <ListAltIcon fontSize="small" /> },
  { label: 'ガントチャート', path: '/gantt', icon: <BarChartIcon fontSize="small" /> },
  { label: 'ダッシュボード', path: '/risk', icon: <DashboardIcon fontSize="small" /> },
  { label: 'グループ管理', path: '/task-groups', icon: <AccountTreeIcon fontSize="small" /> },
  { label: 'フェーズマトリクス', path: '/matrix', icon: <GridOnIcon fontSize="small" /> },
] as const

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()

  /** サイドバーの開閉状態。初期値は開いた状態。 */
  const [open, setOpen] = useState(true)

  /** 現在のパスがナビ項目のパスと一致するか判定する。
   * '/' は完全一致のみ選択。それ以外は前方一致で判定する。
   */
  const isActive = (path: string): boolean =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* トップバー: タイトルとサイドバートグルボタンのみ配置 */}
      <AppBar
        position="fixed"
        elevation={1}
        sx={{ bgcolor: 'primary.main', zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar variant="dense" sx={{ gap: 1 }}>
          <IconButton
            color="inherit"
            aria-label={open ? 'メニューを閉じる' : 'メニューを開く'}
            onClick={() => setOpen((prev) => !prev)}
            edge="start"
          >
            {open ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'inherit', whiteSpace: 'nowrap' }}>
            タスク管理
          </Typography>
        </Toolbar>
      </AppBar>

      {/* サイドバー: persistent Drawer でトグル */}
      <Drawer
        variant="persistent"
        open={open}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {/* AppBar（dense: 48px）分の余白 */}
        <Toolbar variant="dense" />
        <Divider />
        <List dense>
          {NAV_ITEMS.map((item) => (
            <ListItem key={item.path} disablePadding>
              <ListItemButton selected={isActive(item.path)} onClick={() => navigate(item.path)}>
                <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* メインコンテンツ: サイドバー開閉に合わせてマージンをアニメーション
       * ml は Drawer 外枠が常に DRAWER_WIDTH を占有するため、
       * 閉時は -DRAWER_WIDTH で相殺し、開時は 0 にして Drawer の直後に配置する。
       */}
      <Box
        component="main"
        sx={{
          flex: 1,
          mt: '48px', // AppBar dense の高さ
          ml: open ? 0 : `-${DRAWER_WIDTH}px`,
          transition: (theme) =>
            theme.transitions.create('margin-left', {
              easing: open ? theme.transitions.easing.easeOut : theme.transitions.easing.sharp,
              duration: open
                ? theme.transitions.duration.enteringScreen
                : theme.transitions.duration.leavingScreen,
            }),
          minWidth: 0,
        }}
      >
        {children}
      </Box>
    </Box>
  )
}
