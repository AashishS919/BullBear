/**
 * Formatting helpers for financial figures.
 * All currency is Nepalese Rupee (NPR / Rs.). Numbers are rendered in
 * JetBrains Mono with tabular figures at the component level.
 */

const npr = new Intl.NumberFormat('en-IN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const intFmt = new Intl.NumberFormat('en-IN')

/** Rs. 1,23,456.78 (Indian/Nepali grouping) */
export function formatNPR(value) {
  if (value == null || Number.isNaN(value)) return 'Rs. --'
  return `Rs. ${npr.format(value)}`
}

/** 1,23,456 */
export function formatInt(value) {
  if (value == null || Number.isNaN(value)) return '--'
  return intFmt.format(Math.round(value))
}

/** 12.34 (two decimals, no symbol) */
export function formatNum(value, decimals = 2) {
  if (value == null || Number.isNaN(value)) return '--'
  return value.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/** +2.45% / -1.10% with explicit sign */
export function formatPct(value, decimals = 2) {
  if (value == null || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/** +1,234.50 / -56.00 with explicit sign */
export function formatSigned(value, decimals = 2) {
  if (value == null || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNum(value, decimals)}`
}

/** Compact volume: 1.2M, 845.0K */
export function formatVolume(value) {
  if (value == null || Number.isNaN(value)) return '--'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return String(value)
}

/** 2026-06-09 -> Jun 09, 2026 */
export function formatDate(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  })
}

/** Trend direction from a numeric delta: 'up' | 'down' | 'flat' */
export function trendOf(delta) {
  if (delta > 0) return 'up'
  if (delta < 0) return 'down'
  return 'flat'
}
