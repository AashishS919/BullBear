import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { useMarketStream } from '../../hooks/useMarketStream'
import { formatNum, formatVolume } from '../../lib/format'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Range, Select } from '../../components/ui/Input'
import { Badge } from '../../components/ui/Badge'
import { TrendIndicator, PredictionPill } from '../../components/ui/TrendIndicator'
import { LiveStatus } from '../../components/ui/LiveStatus'
import { CandlestickChart } from '../../components/charts/CandlestickChart'
import { PredictionCompareChart } from '../../components/charts/PredictionCompareChart'
import { Loader, ErrorState } from '../../components/ui/State'
import { cn } from '../../lib/cn'

const RANGES = ['1M', '6M', '1Y', '5Y', 'MAX']
// Matches MAX_HORIZON_DAYS in backend/app/schemas/market.py (and HORIZON in ml/config.py).
const MAX_HORIZON = 5
const HORIZON_TICKS = Array.from({ length: MAX_HORIZON }, (_, i) => i + 1)

export function ChartingDashboard() {
  const [params, setParams] = useSearchParams()
  const symbol = (params.get('symbol') || 'NABIL').toUpperCase()
  const [range, setRange] = useState('1Y')
  const [horizon, setHorizon] = useState(1)

  const tickers = useApi(() => api.tickers(), [])
  const series = useApi(() => api.series(symbol, range), [symbol, range])
  const pred = useApi(() => api.predict(symbol, horizon), [symbol, horizon])
  const predSeries = useApi(
    () => api.predictionSeries(symbol, horizon).catch(() => null), [symbol, horizon],
  )
  const { ticks, status } = useMarketStream()

  const candles = series.data?.candles || []
  const livePrice = ticks[symbol]?.price ?? null

  const quote = useMemo(() => {
    if (candles.length < 2) return null
    const last = candles[candles.length - 1]
    const prev = candles[candles.length - 2]
    // Prefer the live tick price over the last historical close when streaming.
    const close = livePrice ?? last.close
    const change = close - prev.close
    return { close, change, changePct: (change / prev.close) * 100 }
  }, [candles, livePrice])

  const periodStats = useMemo(() => {
    if (!candles.length) return null
    const first = candles[0]
    const last = candles[candles.length - 1]
    const change = last.close - first.open
    return {
      high: Math.max(...candles.map((r) => r.high)),
      low: Math.min(...candles.map((r) => r.low)),
      change,
      changePct: (change / first.open) * 100,
      avgVol: candles.reduce((a, r) => a + r.volume, 0) / candles.length,
    }
  }, [candles])

  // Forecast dates are anchored to the last real candle, so stale data silently produces
  // past-dated targets. Surface the anchor instead of letting it look like a model bug.
  const dataAsOf = useMemo(() => {
    if (!candles.length) return null
    const date = String(candles[candles.length - 1].date).slice(0, 10)
    const days = Math.floor((Date.now() - new Date(`${date}T00:00:00`).getTime()) / 86400000)
    return { date, days, stale: days > 7 }
  }, [candles])

  const setSymbol = (s) => setParams({ symbol: s })
  const prediction = pred.data
  const compare = predSeries.data

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4">
          <div className="flex items-center gap-4">
            <Select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="w-56">
              {(tickers.data || [{ symbol, name: symbol }]).map((t) => (
                <option key={t.symbol} value={t.symbol}>{t.symbol} - {t.name}</option>
              ))}
            </Select>
            {quote && (
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-2xl font-semibold tabular-nums text-ink">
                  {formatNum(quote.close)}
                </span>
                <TrendIndicator value={quote.change} pct={quote.changePct} showValue size="lg" />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <LiveStatus status={status} />
            {prediction && (
              <PredictionPill direction={prediction.direction} confidence={prediction.confidence} />
            )}
            <div className="flex rounded-md border border-line-2 p-0.5">
              {RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    'rounded px-3 py-1 text-sm font-medium transition',
                    range === r ? 'bg-accent text-white' : 'text-ink-2 hover:bg-surface-2',
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>

        <CardBody>
          {series.loading ? (
            <Loader label="Loading candles..." />
          ) : series.error ? (
            <ErrorState error={series.error} onRetry={series.reload} />
          ) : (
            <CandlestickChart
              series={candles}
              prediction={prediction}
              horizon={horizon}
              livePrice={livePrice}
            />
          )}
        </CardBody>
      </Card>

      {periodStats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <StatCell label={`${range} Change`}>
            <TrendIndicator value={periodStats.change} pct={periodStats.changePct} showValue />
          </StatCell>
          <StatCell label="Period High" mono>{formatNum(periodStats.high)}</StatCell>
          <StatCell label="Period Low" mono>{formatNum(periodStats.low)}</StatCell>
          <StatCell label="Avg Volume" mono>{formatVolume(periodStats.avgVol)}</StatCell>
          <StatCell label="Data Points" mono>{candles.length}</StatCell>
        </div>
      )}

      <Card>
        <CardHeader
          title="Trend Prediction"
          subtitle={`Forecast ${horizon} trading day${horizon > 1 ? 's' : ''} ahead`}
          action={prediction && <Badge tone="accent">{prediction.model}</Badge>}
        />
        <CardBody className="space-y-4 text-sm text-ink-2">
          <div className="max-w-sm">
            <div className="mb-1.5 flex items-baseline justify-between">
              <label
                htmlFor="horizon"
                className="text-xs font-medium uppercase tracking-wide text-ink-3"
              >
                Forecast horizon
              </label>
              <span className="font-mono text-sm font-semibold text-ink">
                {horizon} day{horizon > 1 ? 's' : ''}
              </span>
            </div>
            <Range
              id="horizon"
              min={1}
              max={MAX_HORIZON}
              step={1}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
            />
            <div className="mt-1 flex justify-between font-mono text-[11px] text-ink-3">
              {HORIZON_TICKS.map((d) => <span key={d}>{d}</span>)}
            </div>
          </div>

          {dataAsOf && (
            <p className={cn('text-xs', dataAsOf.stale ? 'text-bear' : 'text-ink-3')}>
              Data as of <span className="font-mono">{dataAsOf.date}</span> - forecasts run
              from that session.
              {dataAsOf.stale && (
                <> Latest candle is {dataAsOf.days} days old; refresh with{' '}
                <code>scripts/fetch_sharesansar.py</code> then{' '}
                <code>scripts/data_pipeline.py --source sharesansar</code>.</>
              )}
            </p>
          )}

          {prediction ? (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-4">
                <PredictionPill direction={prediction.direction} confidence={prediction.confidence} />
                {prediction.predicted_close != null ? (
                  <span className="font-mono text-ink">
                    Day-{prediction.horizon_days} target: {formatNum(prediction.predicted_close)}
                    {prediction.target_date && (
                      <span className="text-ink-3"> on {prediction.target_date}</span>
                    )}
                    {prediction.last_close != null && (
                      <span className="text-ink-3"> (from {formatNum(prediction.last_close)})</span>
                    )}
                  </span>
                ) : (
                  <span className="text-ink-3">
                    Directional signal only (train the LSTM to see a price target).
                  </span>
                )}
              </div>
              {prediction.horizon_days !== horizon && (
                <p className="text-bear">
                  The stored model output only covers {prediction.horizon_days} day
                  {prediction.horizon_days > 1 ? 's' : ''} - re-run <code>ml/infer.py</code> to
                  publish the full {MAX_HORIZON}-day path.
                </p>
              )}
              <p className="text-ink-3">
                The dashed line on the chart projects the model's forecast path. Green is
                bullish, red bearish.
                {horizon > 1 && (
                  <> Days past the first are an iterative rollout - each step feeds the previous
                  prediction back in as input, so accuracy degrades the further out you look.
                  Compare the backtest metrics below at 1 day and at {horizon} to see by how
                  much.</>
                )}
              </p>
            </div>
          ) : pred.loading ? (
            <Loader label="Running model..." />
          ) : (
            <span className="text-ink-3">No prediction available.</span>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Prediction vs Actual"
          subtitle={`LSTM backtest over the holdout window, scored at ${
            compare?.horizon_days ?? horizon} day${(compare?.horizon_days ?? horizon) > 1 ? 's' : ''}`}
          action={compare && (
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="neutral">MAE {formatNum(compare.metrics.mae)}</Badge>
              <Badge tone="neutral">RMSE {formatNum(compare.metrics.rmse)}</Badge>
              <Badge tone={compare.metrics.directional_accuracy >= 0.5 ? 'bull' : 'bear'}>
                Dir. acc {Math.round(compare.metrics.directional_accuracy * 100)}%
              </Badge>
            </div>
          )}
        />
        <CardBody>
          {predSeries.loading ? (
            <Loader label="Loading backtest..." />
          ) : compare && compare.points.length ? (
            <>
              <PredictionCompareChart points={compare.points} forward={compare.forward} />
              <p className="mt-2 text-sm text-ink-3">
                Solid line is the actual close; dashed is the model's predicted close on unseen
                days, scored at the horizon you selected. The "Forecast" markers are the model's
                projection for the upcoming trading day{compare.horizon_days > 1 ? 's' : ''} - they
                fold into the lines once those real closes land and the backtest re-runs.
              </p>
              {compare.horizon_days !== horizon && (
                <p className="mt-1 text-sm text-bear">
                  No {horizon}-day backtest in the stored artifacts, so these are the
                  {' '}{compare.horizon_days}-day numbers - re-run <code>ml/backtest.py</code> to
                  score every horizon.
                </p>
              )}
            </>
          ) : (
            <span className="text-sm text-ink-3">
              No backtest series yet. Train the LSTM and run <code>ml/backtest.py</code> to compare
              predicted vs actual closes.
            </span>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

function StatCell({ label, mono, children }) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-3">{label}</div>
      <div className={cn('mt-1.5 text-lg font-semibold text-ink', mono && 'font-mono tabular-nums')}>
        {children}
      </div>
    </Card>
  )
}
