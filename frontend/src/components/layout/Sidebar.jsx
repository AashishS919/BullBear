import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, CandlestickChart, Wallet, ArrowLeftRight,
  ReceiptText, Users, Database, TrendingUp,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { cn } from '../../lib/cn'

const NAV = [
  { section: 'Trading', items: [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/charts', label: 'Charts', icon: CandlestickChart },
    { to: '/portfolio', label: 'Portfolio', icon: Wallet },
    { to: '/orders', label: 'Place Order', icon: ArrowLeftRight },
    { to: '/transactions', label: 'Transactions', icon: ReceiptText },
  ]},
  { section: 'Admin', adminOnly: true, items: [
    { to: '/admin/users', label: 'Users', icon: Users },
    { to: '/admin/datasets', label: 'Datasets', icon: Database },
  ]},
]

export function Sidebar() {
  const { user } = useAuth()
  // Only admins see the Admin group; the routes themselves stay guarded by AdminRoute.
  const groups = NAV.filter((g) => !g.adminOnly || user?.role === 'ADMIN')

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface lg:flex">
      <div className="flex h-16 items-center gap-2 border-b border-line px-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-ink text-paper">
          <TrendingUp size={18} strokeWidth={2.5} />
        </span>
        <span className="text-lg font-semibold tracking-tight text-ink">BullBear</span>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {groups.map((group) => (
          <div key={group.section}>
            <p className="px-3 pb-2 text-xs font-medium uppercase tracking-wide text-ink-3">
              {group.section}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition',
                        isActive
                          ? 'bg-accent-soft text-accent'
                          : 'text-ink-2 hover:bg-surface-2',
                      )
                    }
                  >
                    <item.icon size={18} />
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-line px-5 py-3 text-xs text-ink-3">
        Simulated trading. No real funds.
      </div>
    </aside>
  )
}
