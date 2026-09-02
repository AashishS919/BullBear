/**
 * Mock 5-year daily OHLCV data for major Nepalese stock tickers.
 * Deterministic (seeded) so charts render identically across reloads.
 * Spans 2021-01-01 to the current date, skipping weekends to mimic trading days.
 */

// --- Ticker registry (NEPSE-style metadata) ---
export const TICKERS = [
  { symbol: 'NABIL', name: 'Nabil Bank Limited', sector: 'Commercial Bank', base: 520 },
  { symbol: 'NICA', name: 'NIC Asia Bank Limited', sector: 'Commercial Bank', base: 760 },
  { symbol: 'NTC', name: 'Nepal Telecom', sector: 'Telecommunication', base: 980 },
  { symbol: 'NRIC', name: 'Nepal Reinsurance Company', sector: 'Investment', base: 740 },
  { symbol: 'UPPER', name: 'Upper Tamakoshi Hydropower', sector: 'Hydropower', base: 480 },
  { symbol: 'CHCL', name: 'Chilime Hydropower', sector: 'Hydropower', base: 540 },
  { symbol: 'VLBS', name: 'Vijaya Laghubitta Bittiya Sanstha Limited', sector: 'Microfinance', base: 750 },
  { symbol: 'SBL', name: 'Siddhartha Bank Limited', sector: 'Commercial Bank', base: 340 },
  { symbol: 'AHL', name: 'Asian Hydropower Limited', sector: 'Hydropower', base: 250 },
  { symbol: 'ADBL', name: 'Agricultural Development Bank Limited', sector: 'Commercial Bank', base: 300 },
]

// Mulberry32 seeded PRNG for reproducible series.
function mulberry32(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function seedFromString(str) {
  let h = 1779033703 ^ str.length
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353)
    h = (h << 13) | (h >>> 19)
  }
  return (h ^= h >>> 16) >>> 0
}

const START = new Date('2021-01-01')
const END = new Date() // current date; series tracks the real calendar

function tradingDays() {
  const days = []
  const d = new Date(START)
  while (d <= END) {
    const dow = d.getDay()
    if (dow !== 0 && dow !== 6) {
      days.push(d.toISOString().slice(0, 10))
    }
    d.setDate(d.getDate() + 1)
  }
  return days
}

/**
 * Generate a deterministic OHLCV series for one ticker.
 * Returns [{ date, open, high, low, close, volume }] across the full window.
 */
function generateSeries(ticker) {
  const rand = mulberry32(seedFromString(ticker.symbol))
  const days = tradingDays()
  const series = []
  let price = ticker.base

  // Slow multi-year drift so the 5Y zoom shows a real trend, not just noise.
  const drift = (rand() - 0.45) * 0.0006

  for (let i = 0; i < days.length; i++) {
    const shock = (rand() - 0.5) * 0.04 // +/- ~2% daily
    const change = drift + shock
    const open = price
    const close = Math.max(10, open * (1 + change))
    const high = Math.max(open, close) * (1 + rand() * 0.012)
    const low = Math.min(open, close) * (1 - rand() * 0.012)
    const volume = Math.round(40000 + rand() * 260000)

    series.push({
      date: days[i],
      open: round2(open),
      high: round2(high),
      low: round2(low),
      close: round2(close),
      volume,
    })
    price = close
  }
  return series
}

function round2(n) {
  return Math.round(n * 100) / 100
}

// Build once at module load; memoized per ticker.
const SERIES_CACHE = {}

export function getSeries(symbol) {
  if (!SERIES_CACHE[symbol]) {
    const ticker = TICKERS.find((t) => t.symbol === symbol)
    if (!ticker) return []
    SERIES_CACHE[symbol] = generateSeries(ticker)
  }
  return SERIES_CACHE[symbol]
}

/** Latest snapshot row + derived day change for a ticker. */
export function getQuote(symbol) {
  const s = getSeries(symbol)
  if (s.length < 2) return null
  const last = s[s.length - 1]
  const prev = s[s.length - 2]
  const change = round2(last.close - prev.close)
  const changePct = round2((change / prev.close) * 100)
  const meta = TICKERS.find((t) => t.symbol === symbol)
  return { ...meta, ...last, prevClose: prev.close, change, changePct }
}

/** Quotes for the full market table. */
export function getMarketQuotes() {
  return TICKERS.map((t) => getQuote(t.symbol)).filter(Boolean)
}

/** Last N closes for sparklines. */
export function getSparkline(symbol, n = 30) {
  const s = getSeries(symbol)
  return s.slice(-n).map((r) => r.close)
}

/** NEPSE-style index = volume-weighted average of all ticker closes (mock). */
export function getIndexSeries(n = 250) {
  const all = TICKERS.map((t) => getSeries(t.symbol))
  const len = all[0].length
  const out = []
  for (let i = Math.max(0, len - n); i < len; i++) {
    let sum = 0
    for (const s of all) sum += s[i].close
    out.push({ date: all[0][i].date, value: round2(sum / all.length) })
  }
  return out
}

/**
 * Filter a series to a time range relative to the latest date.
 * range: '1M' | '6M' | '1Y' | '5Y' | 'MAX'
 */
export function filterByRange(series, range) {
  if (!series.length || range === 'MAX' || range === '5Y') return series
  const days = { '1M': 22, '6M': 132, '1Y': 252 }[range] ?? series.length
  return series.slice(-days)
}
