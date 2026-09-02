import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Activity, BarChart3, TrendingUp, Wallet } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { useMarketStream } from '../../hooks/useMarketStream'
import { formatNPR, formatNum, formatVolume } from '../../lib/format'
import { Card, CardHeader } from '../../components/ui/Card'
import { StatTile } from '../../components/ui/StatTile'
import { Badge } from '../../components/ui/Badge'
import { TrendIndicator, PredictionPill } from '../../components/ui/TrendIndicator'
import { LiveStatus } from '../../components/ui/LiveStatus'
import { Table, THead, TBody, TR, TH, TD } from '../../components/ui/Table'
import { Sparkline } from '../../components/charts/Sparkline'
import { Loader, ErrorState } from '../../components/ui/State'

export function MarketDashboard() {
  const market = useApi(() => api.overview(), [])
  const portfolio = useApi(() => api.portfolio(), [])
  const { ticks, status } = useMarketStream()

  // Merge live ticks over the fetched quotes so LTP/Change update in place.
  const rows = useMemo(() => {
    const base = market.data || []
    return base.map((q) => {
      const t = ticks[q.symbol]
      if (!t) return q
      return { ...q, close: t.price, change: t.change, change_pct: t.change_pct }
    })
  }, [market.data, ticks])

  if (market.loading || portfolio.loading) return <Loader />
  if (market.error) return <ErrorState error={market.error} onRetry={market.reload} />

  const summary = portfolio.data?.summary
  const gainers = rows.filter((q) => q.change_pct > 0).length

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Net Worth" value={summary ? formatNPR(summary.net_worth) : '--'} icon={Wallet} />
        <StatTile
          label="Portfolio P/L"
          value={summary ? formatNPR(summary.pnl) : '--'}
          deltaPct={summary?.pnl_pct}
          icon={TrendingUp}
        />
        <StatTile label="Advancers" value={`${gainers} / ${rows.length}`} icon={Activity} />
        <StatTile
          label="Total Volume"
          value={formatVolume(rows.reduce((a, q) => a + q.volume, 0))}
          icon={BarChart3}
        />
      </div>

      <Card>
        <CardHeader
          title="Market Watch"
          subtitle="Live quotes and LSTM trend signals"
          action={<LiveStatus status={status} />}
        />
        <Table>
          <THead>
            <TR>
              <TH>Symbol</TH>
              <TH>Sector</TH>
              <TH align="right">LTP</TH>
              <TH align="right">Change</TH>
              <TH align="right">Volume</TH>
              <TH align="center">30D</TH>
              <TH align="center">Signal</TH>
              <TH align="right"></TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((q) => (
              <TR key={q.symbol}>
                <TD>
                  <div className="font-mono font-semibold text-ink">{q.symbol}</div>
                  <div className="text-xs text-ink-3">{q.name}</div>
                </TD>
                <TD><Badge tone="neutral">{q.sector}</Badge></TD>
                <TD align="right" mono>{formatNum(q.close)}</TD>
                <TD align="right">
                  <TrendIndicator value={q.change} pct={q.change_pct} showValue />
                </TD>
                <TD align="right" mono>{formatVolume(q.volume)}</TD>
                <TD align="center">
                  <div className="flex justify-center">
                    {q.spark?.length ? <Sparkline data={q.spark} /> : <span className="text-ink-3">--</span>}
                  </div>
                </TD>
                <TD align="center">
                  {q.direction
                    ? <PredictionPill direction={q.direction} confidence={q.confidence} />
                    : <span className="text-xs text-ink-3">No model</span>}
                </TD>
                <TD align="right">
                  <Link to={`/charts?symbol=${q.symbol}`} className="text-sm font-medium text-accent hover:underline">
                    View
                  </Link>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  )
}
