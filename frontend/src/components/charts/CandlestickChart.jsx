import { useMemo } from 'react'
import ReactApexChart from 'react-apexcharts'
import { CHART } from './palette'

/**
 * OHLC candlestick 
 */
export function CandlestickChart({ series, prediction, horizon = 1, livePrice = null, height = 380 }) {
  const candleData = useMemo(() => {
    const data = series.map((r) => ({
      x: new Date(r.date).getTime(),
      y: [r.open, r.high, r.low, r.close],
    }))
    if (livePrice != null && data.length) {
      const last = data[data.length - 1]
      const [o, h, l] = last.y
      data[data.length - 1] = { ...last, y: [o, Math.max(h, livePrice), Math.min(l, livePrice), livePrice] }
    }
    return data
  }, [series, livePrice])
  const closeData = useMemo(() => {
    const data = series.map((r) => ({ x: new Date(r.date).getTime(), y: r.close }))
    if (livePrice != null && data.length) {
      data[data.length - 1] = { ...data[data.length - 1], y: livePrice }
    }
    return data
  }, [series, livePrice])

  const lastTime = series.length ? new Date(series[series.length - 1].date).getTime() : 0

  // Each rollout step carries its own target_date, so the overlay lands on the real
  // trading calendar instead of assuming one step is one clock day (weekends broke that).
  const forecastPoints = useMemo(() => {
    if (!prediction || prediction.last_close == null || !series.length) return []
    const steps = (prediction.path || [])
      .filter((p) => p.step <= horizon && p.predicted_close != null)
      .map((p) => ({ x: new Date(p.target_date).getTime(), y: p.predicted_close }))
    if (!steps.length) {
      // No path (stub model, or artifacts predating multi-horizon): single-day fallback.
      if (prediction.predicted_close == null) return []
      steps.push({ x: lastTime + 24 * 60 * 60 * 1000, y: prediction.predicted_close })
    }
    return [{ x: lastTime, y: prediction.last_close }, ...steps]
  }, [prediction, horizon, series, lastTime])

  const hasForecast = forecastPoints.length > 1
  const lastForecast = hasForecast ? forecastPoints[forecastPoints.length - 1] : null
  const fcColor = prediction?.direction === 'down' ? CHART.bear : CHART.bull

  const forecastSeries = hasForecast
    ? [{ name: 'LSTM forecast', type: 'line', data: forecastPoints }]
    : []

  const selMin = candleData.length ? candleData[Math.floor(candleData.length * 0.8)].x : undefined
  const selMax = candleData.length ? candleData[candleData.length - 1].x : undefined

  const mainOptions = {
    chart: {
      id: 'bb-candles',
      type: 'candlestick',
      height,
      toolbar: { autoSelected: 'pan', show: true, tools: { download: false } },
      fontFamily: 'DM Sans, sans-serif',
      background: 'transparent',
      animations: { enabled: false },
    },
    grid: { borderColor: CHART.line, strokeDashArray: 3 },
    xaxis: { type: 'datetime', labels: { style: { colors: CHART.ink3 } } },
    yaxis: {
      tooltip: { enabled: true },
      labels: {
        style: { colors: CHART.ink3, fontFamily: 'JetBrains Mono, monospace' },
        formatter: (v) => v.toFixed(0),
      },
    },
    // index 0 = candlestick (uses plotOptions), index 1 = forecast line.
    colors: [CHART.ink, fcColor],
    stroke: { width: [1, 2], dashArray: [0, 6], curve: 'straight' },
    markers: { size: hasForecast ? [0, 5] : [0], colors: [fcColor], strokeColors: '#fff', strokeWidth: 2 },
    plotOptions: {
      candlestick: { colors: { upward: CHART.bull, downward: CHART.bear }, wick: { useFillColor: true } },
    },
    legend: { show: false },
    tooltip: { theme: 'light' },
    annotations: hasForecast
      ? {
          // Label only the final day so a 5-step path does not stack five boxes.
          points: [{
            x: lastForecast.x,
            y: lastForecast.y,
            marker: { size: 0 },
            label: {
              text: `LSTM ${lastForecast.y.toFixed(2)}`,
              borderColor: fcColor,
              style: { color: '#fff', background: fcColor, fontFamily: 'JetBrains Mono, monospace' },
            },
          }],
        }
      : {},
  }

  const brushOptions = {
    chart: {
      id: 'bb-brush',
      height: 120,
      type: 'area',
      brush: { target: 'bb-candles', enabled: true },
      selection: { enabled: true, xaxis: selMin && selMax ? { min: selMin, max: selMax } : undefined },
      toolbar: { show: false },
      fontFamily: 'DM Sans, sans-serif',
      background: 'transparent',
    },
    colors: [CHART.accent],
    stroke: { width: 1.5 },
    fill: { type: 'gradient', gradient: { opacityFrom: 0.25, opacityTo: 0.02 } },
    grid: { borderColor: CHART.line },
    xaxis: { type: 'datetime', labels: { style: { colors: CHART.ink3 } } },
    yaxis: { show: false },
    tooltip: { enabled: false },
    legend: { show: false },
    dataLabels: { enabled: false },
  }

  return (
    <div>
      <ReactApexChart
        options={mainOptions}
        series={[{ name: 'Price', type: 'candlestick', data: candleData }, ...forecastSeries]}
        type="candlestick"
        height={height}
      />
      <ReactApexChart
        options={brushOptions}
        series={[{ name: 'Close', data: closeData }]}
        type="area"
        height={120}
      />
    </div>
  )
}
