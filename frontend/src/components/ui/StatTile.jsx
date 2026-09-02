import { cn } from '../../lib/cn'
import { Card } from './Card'
import { TrendIndicator } from './TrendIndicator'

/**
 * Compact KPI tile: label, large mono value, optional trend delta.
 */
export function StatTile({ label, value, delta, deltaPct, icon: Icon, className }) {
  return (
    <Card className={cn('p-4', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-3">{label}</span>
        {Icon && <Icon size={16} className="text-ink-3" />}
      </div>
      <div className="mt-2 font-mono text-2xl font-semibold tabular-nums text-ink">{value}</div>
      {(delta != null || deltaPct != null) && (
        <div className="mt-1">
          <TrendIndicator value={delta ?? deltaPct} pct={deltaPct} showValue={delta != null} />
        </div>
      )}
    </Card>
  )
}
