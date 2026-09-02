import { TrendingUp } from 'lucide-react'

/** Split-panel auth shell: brand panel + form card. */
export function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen bg-paper">
      <div className="hidden w-1/2 flex-col justify-between bg-ink p-12 text-paper lg:flex">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-paper text-ink">
            <TrendingUp size={20} strokeWidth={2.5} />
          </span>
          <span className="text-xl font-semibold">BullBear Stock</span>
        </div>
        <div>
          <h2 className="text-3xl font-semibold leading-tight">
            Predict the trend.<br />Trade with conviction.
          </h2>
          <p className="mt-4 max-w-md text-paper/70">
            LSTM-driven trend signals on five years of Nepalese market data, with a fully
            simulated trading environment. No real funds at risk.
          </p>
        </div>
        <p className="text-sm text-paper/50">Simulated trading platform for educational use.</p>
      </div>

      <div className="flex w-full items-center justify-center p-6 lg:w-1/2">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-3">{subtitle}</p>}
          <div className="mt-6">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-ink-3">{footer}</div>}
        </div>
      </div>
    </div>
  )
}
