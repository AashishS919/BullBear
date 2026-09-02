import { useRef, useState } from 'react'
import { Wallet, Coins, PiggyBank, TrendingUp, Upload } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { formatNPR, formatNum } from '../../lib/format'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { StatTile } from '../../components/ui/StatTile'
import { TrendIndicator } from '../../components/ui/TrendIndicator'
import { Table, THead, TBody, TR, TH, TD } from '../../components/ui/Table'
import { Loader, ErrorState, EmptyState } from '../../components/ui/State'

export function PortfolioTracker() {
  const { data, loading, error, reload } = useApi(() => api.portfolio(), [])

  // Only block the whole page on the FIRST load. On a reload (e.g. after an import)
  // keep the current view mounted so the import result banner isn't destroyed.
  if (loading && !data) return <Loader />
  if (error && !data) return <ErrorState error={error} onRetry={reload} />

  const { positions, summary } = data

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Net Worth" value={formatNPR(summary.net_worth)} icon={Wallet} />
        <StatTile label="Holdings Value" value={formatNPR(summary.market_value)} icon={Coins} />
        <StatTile label="Cash Balance" value={formatNPR(summary.cash)} icon={PiggyBank} />
        <StatTile label="Unrealized P/L" value={formatNPR(summary.pnl)} deltaPct={summary.pnl_pct} icon={TrendingUp} />
      </div>

      {positions.length > 0 && <ActionSummary positions={positions} />}

      <Card>
        <CardHeader
          title="Holdings"
          subtitle="Current positions and unrealized profit / loss"
          action={<ImportPortfolio onImported={reload} />}
        />
        {positions.length === 0 ? (
          <EmptyState message="No holdings yet. Place a buy order to get started." />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Symbol</TH>
                <TH align="right">Qty</TH>
                <TH align="right">Avg Cost</TH>
                <TH align="right">LTP</TH>
                <TH align="right">Invested</TH>
                <TH align="right">Mkt Value</TH>
                <TH align="right">P/L</TH>
                <TH align="right">Day</TH>
                <TH align="right">Signal</TH>
              </TR>
            </THead>
            <TBody>
              {positions.map((p) => (
                <TR key={p.symbol}>
                  <TD>
                    <div className="font-mono font-semibold">{p.symbol}</div>
                    <div className="text-xs text-ink-3">{p.name}</div>
                  </TD>
                  <TD align="right" mono>{p.qty}</TD>
                  <TD align="right" mono>{formatNum(p.avg_cost)}</TD>
                  <TD align="right" mono>{formatNum(p.ltp)}</TD>
                  <TD align="right" mono>{formatNPR(p.invested)}</TD>
                  <TD align="right" mono>{formatNPR(p.market_value)}</TD>
                  <TD align="right"><TrendIndicator value={p.pnl} pct={p.pnl_pct} showValue /></TD>
                  <TD align="right"><TrendIndicator value={p.day_change_pct} pct={p.day_change_pct} /></TD>
                  <TD align="right"><RecommendationBadge rec={p.recommendation} /></TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  )
}

const TONE_BY_ACTION = { BUY: 'bull', SELL: 'bear', HOLD: 'neutral' }
// SELL first: a position to exit is more time-sensitive than one to add to.
const ACTION_ORDER = { SELL: 0, BUY: 1, HOLD: 2 }

function RecommendationBadge({ rec }) {
  if (!rec) return <span className="text-ink-3">-</span>
  return (
    <span className="inline-flex items-center gap-1" title={rec.reason}>
      <Badge tone={TONE_BY_ACTION[rec.action] ?? 'neutral'}>{rec.action}</Badge>
      {/* A gated HOLD is a suppressed call, not a considered one - mark the difference. */}
      {!rec.reliable && <span className="text-xs text-ink-3">*</span>}
    </span>
  )
}

/**
 * Groups the per-position calls so the user sees what to act on without reading every row.
 * Counts cover all holdings; only actionable (non-HOLD) calls get their reasoning spelled
 * out, since a list of "do nothing" reasons is noise.
 */
function ActionSummary({ positions }) {
  const counts = { BUY: 0, SELL: 0, HOLD: 0 }
  let gated = 0
  for (const p of positions) {
    const rec = p.recommendation
    if (!rec) continue
    counts[rec.action] = (counts[rec.action] ?? 0) + 1
    if (!rec.reliable) gated += 1
  }

  const actionable = positions
    .filter((p) => p.recommendation && p.recommendation.action !== 'HOLD')
    .sort((a, b) => ACTION_ORDER[a.recommendation.action] - ACTION_ORDER[b.recommendation.action])

  const horizon = positions.find((p) => p.recommendation)?.recommendation?.horizon_days ?? 5

  return (
    <Card>
      <CardHeader
        title="Recommended Actions"
        subtitle={`From the ${horizon}-day forecast and your cost basis`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            {counts.SELL > 0 && <Badge tone="bear">{counts.SELL} sell</Badge>}
            {counts.BUY > 0 && <Badge tone="bull">{counts.BUY} buy</Badge>}
            {counts.HOLD > 0 && <Badge tone="neutral">{counts.HOLD} hold</Badge>}
          </div>
        }
      />
      <CardBody className="space-y-3 text-sm">
        {actionable.length === 0 ? (
          <p className="text-ink-3">
            Nothing to act on - every holding is a hold at the {horizon}-day horizon.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {actionable.map((p) => (
              <li key={p.symbol} className="flex flex-wrap items-baseline gap-2">
                <Badge tone={TONE_BY_ACTION[p.recommendation.action]}>
                  {p.recommendation.action}
                </Badge>
                <span className="font-mono font-semibold text-ink">{p.symbol}</span>
                <span className="text-ink-2">{p.recommendation.reason}</span>
                <span className="text-ink-3">
                  Now {formatNum(p.ltp)}, target {formatNum(p.recommendation.target_close)};
                  you hold {p.qty} at {formatNum(p.avg_cost)}.
                </span>
              </li>
            ))}
          </ul>
        )}

        {gated > 0 && (
          <p className="text-xs text-ink-3">
            * {gated} holding{gated > 1 ? 's are' : ' is'} held back because the model
            backtests at or below a coin flip on that ticker, so no directional call is
            made. Hover the signal for details.
          </p>
        )}

        <p className="border-t border-line pt-3 text-xs text-ink-3">
          Model-generated signals from a student project, for learning and demonstration -
          not financial advice. Past backtest accuracy does not guarantee future results.
        </p>
      </CardBody>
    </Card>
  )
}

// Upload a CSV/PDF portfolio; merges into holdings server-side, then reloads the table.
function ImportPortfolio({ onImported }) {
  const inputRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState(null)

  const onPick = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = '' // allow re-selecting the same file
    if (!file) return
    setBusy(true)
    setErr(null)
    setResult(null)
    try {
      const res = await api.importPortfolio(file)
      setResult(res)
      onImported?.()
    } catch (ex) {
      setErr(ex.message || 'Import failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.pdf"
        onChange={onPick}
        className="hidden"
      />
      <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()} disabled={busy}>
        <Upload size={15} />
        {busy ? 'Importing...' : 'Import portfolio'}
      </Button>
      <span className="text-xs text-ink-3">CSV or PDF · Meroshare export supported</span>
      {result && (
        <div className="mt-1 max-w-xs text-right text-xs">
          <span className="font-medium text-bull">Imported {result.imported}</span>
          {result.skipped > 0 && <span className="text-ink-3"> · skipped {result.skipped}</span>}
          {result.warnings?.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-left text-ink-3">
              {result.warnings.slice(0, 5).map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
              {result.warnings.length > 5 && <li>• +{result.warnings.length - 5} more…</li>}
            </ul>
          )}
        </div>
      )}
      {err && <span className="max-w-xs text-right text-xs text-bear">{err}</span>}
    </div>
  )
}
