import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { AdminRoute, ProtectedRoute } from './components/RouteGuards'
import { MarketDashboard } from './features/dashboard/MarketDashboard'
import { ChartingDashboard } from './features/charts/ChartingDashboard'
import { PortfolioTracker } from './features/portfolio/PortfolioTracker'
import { OrderPanel } from './features/orders/OrderPanel'
import { TransactionLog } from './features/transactions/TransactionLog'
import { AdminUsers } from './features/admin/AdminUsers'
import { DatasetManager } from './features/admin/DatasetManager'
import { Login } from './features/auth/Login'
import { Register } from './features/auth/Register'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/register', element: <Register /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <MarketDashboard /> },
      { path: 'charts', element: <ChartingDashboard /> },
      { path: 'portfolio', element: <PortfolioTracker /> },
      { path: 'orders', element: <OrderPanel /> },
      { path: 'transactions', element: <TransactionLog /> },
      { path: 'admin/users', element: <AdminRoute><AdminUsers /></AdminRoute> },
      { path: 'admin/datasets', element: <AdminRoute><DatasetManager /></AdminRoute> },
    ],
  },
])
