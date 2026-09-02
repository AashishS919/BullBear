import ReactApexChart from 'react-apexcharts'
import { CHART } from './palette'

/**
 * Tiny inline trend line for table rows. Colored bull/bear by net direction.
 */
export function Sparkline({ data, width = 96, height = 32 }) {
  const up = data.length > 1 && data[data.length - 1] >= data[0]
  const color = up ? CHART.bull : CHART.bear

  const options = {
    chart: {
      type: 'line',
      sparkline: { enabled: true },
      animations: { enabled: false },
    },
    stroke: { width: 1.75, curve: 'smooth' },
    colors: [color],
    tooltip: { enabled: false },
  }

  return (
    <div style={{ width, height }}>
      <ReactApexChart
        options={options}
        series={[{ data }]}
        type="line"
        width={width}
        height={height}
      />
    </div>
  )
}
