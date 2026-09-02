import { useMemo } from 'react'
import ReactApexChart from 'react-apexcharts'
import { CHART } from './palette'

/**
 * Predicted vs actual close over the LSTM holdout window
 */
export function PredictionCompareChart({ points = [], forward = [], height = 320 }) {
  const actualData = useMemo(
    () => points.map((p) => ({ x: new Date(p.date).getTime(), y: p.actual })),
    [points],
  )
  const predictedData = useMemo(
    () => points.map((p) => ({ x: new Date(p.date).getTime(), y: p.predicted })),
    [points],
  )
  const forwardData = useMemo(
    () => forward.map((f) => ({
      x: new Date(f.target_date).getTime(),
      y: f.predicted_close,
      step: f.step,
    })),
    [forward],
  )

  const series = [
    { name: 'Actual', type: 'line', data: actualData },
    { name: 'Predicted', type: 'line', data: predictedData },
  ]
  if (forwardData.length) {
    series.push({ name: 'Forecast', type: 'line', data: forwardData })
  }

  const options = {
    chart: {
      id: 'bb-pred-compare',
      height,
      type: 'line',
      toolbar: { show: false },
      fontFamily: 'DM Sans, sans-serif',
      background: 'transparent',
      animations: { enabled: false },
    },
    colors: [CHART.ink, CHART.accent, CHART.bull],
    stroke: { width: [2, 2, 2], dashArray: [0, 6, 4], curve: 'straight' },
    markers: { size: [0, 0, 5], strokeColors: '#fff', strokeWidth: 2 },
    grid: { borderColor: CHART.line, strokeDashArray: 3 },
    xaxis: { type: 'datetime', labels: { style: { colors: CHART.ink3 } } },
    yaxis: {
      labels: {
        style: { colors: CHART.ink3, fontFamily: 'JetBrains Mono, monospace' },
        formatter: (v) => v.toFixed(0),
      },
    },
    legend: { show: true, position: 'top', horizontalAlign: 'right', labels: { colors: CHART.ink3 } },
    tooltip: { theme: 'light', shared: true, x: { format: 'dd MMM yyyy' } },
    annotations: forwardData.length
      ? {
          // Only the furthest step is labelled: the forecast days sit within a few
          // sessions of each other at the right edge, so per-point boxes would collide.
          points: [(() => {
            const p = forwardData[forwardData.length - 1]
            return {
              x: p.x,
              y: p.y,
              marker: { size: 0 },
              label: {
                text: p.step ? `D${p.step} ${p.y.toFixed(2)}` : `Next ${p.y.toFixed(2)}`,
                borderColor: CHART.bull,
                style: { color: '#fff', background: CHART.bull, fontFamily: 'JetBrains Mono, monospace' },
              },
            }
          })()],
        }
      : {},
  }

  return <ReactApexChart options={options} series={series} type="line" height={height} />
}
