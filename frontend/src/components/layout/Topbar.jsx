import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, LogOut, Search } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { useAuth } from '../../context/AuthContext'
import { formatNum } from '../../lib/format'
import { TrendIndicator } from '../ui/TrendIndicator'

export function Topbar({ title }) {
  const { user, logout } = useAuth()
  const { data: quotes } = useApi(() => api.quotes(), [])

  // Simple NEPSE-style index = average close across tracked tickers.
  let idx = null
  let changePct = 0
  if (quotes?.length) {
    idx = quotes.reduce((a, q) => a + q.close, 0) / quotes.length
    changePct = quotes.reduce((a, q) => a + q.change_pct, 0) / quotes.length
  }

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-line bg-surface px-5">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
        {idx != null && (
          <div className="hidden items-center gap-2 rounded-md bg-surface-2 px-3 py-1.5 md:flex">
            <span className="text-xs font-medium uppercase text-ink-3">NEPSE</span>
            <span className="font-mono text-sm font-semibold tabular-nums text-ink">{formatNum(idx)}</span>
            <TrendIndicator value={changePct} pct={changePct} />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <TickerSearch />
        <button className="rounded-md p-2 text-ink-2 hover:bg-surface-2" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <div className="hidden text-right sm:block">
            <div className="text-sm font-medium leading-tight text-ink">{user?.name}</div>
            <div className="text-xs leading-tight text-ink-3">{user?.role}</div>
          </div>
          <button
            onClick={logout}
            className="rounded-md p-2 text-ink-2 hover:bg-surface-2"
            title="Log out"
            aria-label="Log out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  )
}

// Filtered ticker search: type a symbol/name, pick a result (or press Enter on the
// first match) to jump to that symbol's chart via the /charts?symbol= route.
function TickerSearch() {
  const navigate = useNavigate()
  const { data: tickers } = useApi(() => api.tickers(), [])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const q = query.trim().toLowerCase()
  const matches = q
    ? (tickers || [])
        .filter((t) => t.symbol.toLowerCase().includes(q) || (t.name || '').toLowerCase().includes(q))
        .slice(0, 8)
    : []

  const go = (symbol) => {
    if (!symbol) return
    navigate(`/charts?symbol=${symbol.toUpperCase()}`)
    setQuery('')
    setOpen(false)
  }

  const onSubmit = (e) => {
    e.preventDefault()
    go(matches[0]?.symbol || query)
  }

  return (
    <form
      onSubmit={onSubmit}
      className="relative hidden lg:block"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false)
      }}
    >
      <div className="flex items-center gap-2 rounded-md border border-line-2 bg-surface px-3">
        <Search size={16} className="text-ink-3" />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
          placeholder="Search ticker..."
          className="h-9 w-44 bg-transparent text-sm text-ink placeholder:text-ink-3 focus:outline-none"
        />
      </div>
      {open && matches.length > 0 && (
        <ul className="absolute z-20 mt-1 w-64 overflow-hidden rounded-md border border-line-2 bg-surface shadow-lg">
          {matches.map((t) => (
            <li key={t.symbol}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => go(t.symbol)}
                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-surface-2"
              >
                <span className="font-mono font-semibold text-ink">{t.symbol}</span>
                <span className="truncate text-xs text-ink-3">{t.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  )
}
