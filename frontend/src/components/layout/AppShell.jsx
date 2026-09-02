import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const TITLES = {
  '/': 'Market Dashboard',
  '/charts': 'Charting',
  '/portfolio': 'Portfolio',
  '/orders': 'Place Order',
  '/transactions': 'Transactions',
  '/admin/users': 'User Management',
  '/admin/datasets': 'Dataset Management',
}

export function AppShell() {
  const { pathname } = useLocation()
  const title = TITLES[pathname] ?? 'BullBear Stock'

  return (
    <div className="flex h-screen overflow-hidden bg-paper">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto p-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
