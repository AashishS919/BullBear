/**
 * Mock user portfolio derived from live mock quotes so P/L is internally
 * consistent with the dashboard prices.
 */
import { getQuote } from './stocks'

const HOLDINGS = [
  { symbol: 'NABIL', qty: 120, avgCost: 470.0 },
  { symbol: 'NICA', qty: 80, avgCost: 690.5 },
  { symbol: 'NTC', qty: 50, avgCost: 905.0 },
  { symbol: 'UPPER', qty: 200, avgCost: 512.25 },
]

export const CASH_BALANCE = 185400.0

export function getPortfolio() {
  const positions = HOLDINGS.map((h) => {
    const quote = getQuote(h.symbol)
    const ltp = quote?.close ?? h.avgCost
    const invested = h.qty * h.avgCost
    const marketValue = h.qty * ltp
    const pnl = marketValue - invested
    const pnlPct = (pnl / invested) * 100
    return {
      symbol: h.symbol,
      name: quote?.name ?? h.symbol,
      qty: h.qty,
      avgCost: h.avgCost,
      ltp,
      dayChangePct: quote?.changePct ?? 0,
      invested,
      marketValue,
      pnl,
      pnlPct,
    }
  })

  const invested = positions.reduce((a, p) => a + p.invested, 0)
  const marketValue = positions.reduce((a, p) => a + p.marketValue, 0)
  const pnl = marketValue - invested
  const pnlPct = invested ? (pnl / invested) * 100 : 0

  return {
    positions,
    summary: {
      invested,
      marketValue,
      pnl,
      pnlPct,
      cash: CASH_BALANCE,
      netWorth: marketValue + CASH_BALANCE,
    },
  }
}
