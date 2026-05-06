/**
 * フロントエンドのルーティング定義。
 * 仕様: README.md
 * 業務制約: 実装途中の画面参照を避け、現存ソースのみで起動可能に保つ
 */
import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'
import AppLayout from './components/AppLayout'

const SCR001_TicketListPage = lazy(
  () => import('./pages/SCR001_TicketListPage'),
)
const SCR002_GanttChartPage = lazy(
  () => import('./pages/SCR002_GanttChartPage'),
)
const SCR003_RiskDashboardPage = lazy(
  () => import('./pages/SCR003_RiskDashboardPage'),
)

function PageLoader() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
      <CircularProgress />
    </Box>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/tickets" replace />} />
            <Route path="/tickets" element={<SCR001_TicketListPage />} />
            <Route path="/gantt" element={<SCR002_GanttChartPage />} />
            <Route path="/risk" element={<SCR003_RiskDashboardPage />} />
          </Routes>
        </AppLayout>
      </Suspense>
    </BrowserRouter>
  )
}
