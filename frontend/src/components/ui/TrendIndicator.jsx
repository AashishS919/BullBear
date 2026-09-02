import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { cn } from '../../lib/cn'
import { formatPct, formatSigned, trendOf } from '../../lib/format'

/**
 * Directional figure: green up / red down per the bull/bear palette.
 * Pass `value` (a delta) and optionally `pct` to show "+12.50 (+2.45%)".
 */
export function TrendIndicator({ value, pct, showValue = false, className, size = 'sm' }) {
  const dir = trendOf(value)
  const Icon = dir === 'up' ? ArrowUpRight : dir === 'down' ? ArrowDownRight : Minus
  const color = dir === 'up' ? 'text-bull' : dir === 'down' ? 'text-bear' : 'text-ink-3'
  const iconSize = size === 'lg' ? 18 : 14

  return (
    <span className={cn('inline-flex items-center gap-1 font-mono tabular-nums font-medium', color, className)}>
      <Icon size={iconSize} strokeWidth={2.5} />
      {showValue && value != null && <span>{formatSigned(value)}</span>}
      {pct != null && <span>{formatPct(pct)}</span>}
    </span>
  )
}

/** Up / Down prediction pill for the LSTM trend signal. */
export function PredictionPill({ direction, confidence }) {
  const up = direction === 'up'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold',
        up ? 'bg-bull-soft text-bull' : 'bg-bear-soft text-bear',
      )}
    >
      {up ? <ArrowUpRight size={14} strokeWidth={2.5} /> : <ArrowDownRight size={14} strokeWidth={2.5} />}
      {up ? 'Bullish' : 'Bearish'}
      {confidence != null && <span className="font-mono opacity-80">{Math.round(confidence * 100)}%</span>}
    </span>
  )
}
