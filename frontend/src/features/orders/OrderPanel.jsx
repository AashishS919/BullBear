import { useMemo, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { formatNPR, formatNum } from '../../lib/format'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Field, Input, Select } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Loader, ErrorState } from '../../components/ui/State'
import { cn } from '../../lib/cn'

const BROKER_FEE = 0.0036

export function OrderPanel() {
  const quotes = useApi(() => api.quotes(), [])
  const portfolio = useApi(() => api.portfolio(), [])

  const [side, setSide] = useState('BUY')
  const [symbol, setSymbol] = useState('NABIL')
  const [orderType, setOrderType] = useState('MARKET')
  const [qty, setQty] = useState('')
  const [limitPrice, setLimitPrice] = useState('')
  const [confirmed, setConfirmed] = useState(null)
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  const quoteMap = useMemo(() => {
    const m = {}
    for (const q of quotes.data || []) m[q.symbol] = q
    return m
  }, [quotes.data])

  const cash = portfolio.data?.summary?.cash ?? 0
  const marketPrice = quoteMap[symbol]?.close ?? 0
  const price = orderType === 'LIMIT' && limitPrice ? Number(limitPrice) : marketPrice
  const qtyNum = Number(qty) || 0

  const { subtotal, fee, total } = useMemo(() => {
    const sub = qtyNum * price
    const f = sub * BROKER_FEE
    return { subtotal: sub, fee: f, total: side === 'BUY' ? sub + f : sub - f }
  }, [qtyNum, price, side])

  const errors = useMemo(() => {
    const e = {}
    if (qty !== '' && (!Number.isInteger(qtyNum) || qtyNum <= 0)) e.qty = 'Enter a whole number greater than 0.'
    if (orderType === 'LIMIT' && limitPrice !== '' && Number(limitPrice) <= 0) e.limitPrice = 'Limit price must be positive.'
    if (side === 'BUY' && total > cash) e.qty = 'Order exceeds available cash balance.'
    return e
  }, [qty, qtyNum, orderType, limitPrice, side, total, cash])

  const canSubmit = qtyNum > 0 && Object.keys(errors).length === 0 &&
    (orderType === 'MARKET' || Number(limitPrice) > 0)

  async function submit(e) {
    e.preventDefault()
    setServerError('')
    if (!canSubmit) return
    setBusy(true)
    try {
      const order = await api.placeOrder({
        symbol, side, order_type: orderType, qty: qtyNum,
        limit_price: orderType === 'LIMIT' ? Number(limitPrice) : null,
      })
      setConfirmed(order)
      setQty(''); setLimitPrice('')
      portfolio.reload()
    } catch (err) {
      setServerError(err.message || 'Order failed.')
    } finally {
      setBusy(false)
    }
  }

  if (quotes.loading || portfolio.loading) return <Loader />
  if (quotes.error) return <ErrorState error={quotes.error} onRetry={quotes.reload} />

  const tickers = quotes.data || []

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader title="Place Order" subtitle="Simulated trading - no real funds are used" />
        <CardBody>
          <form onSubmit={submit} className="space-y-5">
            <div className="flex rounded-md border border-line-2 p-1">
              {['BUY', 'SELL'].map((s) => (
                <button
                  key={s} type="button" onClick={() => setSide(s)}
                  className={cn(
                    'flex-1 rounded py-2 text-sm font-semibold transition',
                    side === s
                      ? s === 'BUY' ? 'bg-bull text-white' : 'bg-bear text-white'
                      : 'text-ink-2 hover:bg-surface-2',
                  )}
                >
                  {s}
                </button>
              ))}
            </div>

            <Field label="Stock" htmlFor="symbol" required>
              <Select id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                {tickers.map((t) => (
                  <option key={t.symbol} value={t.symbol}>{t.symbol} - {t.name}</option>
                ))}
              </Select>
            </Field>

            <Field label="Order Type" htmlFor="otype">
              <Select id="otype" value={orderType} onChange={(e) => setOrderType(e.target.value)}>
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
              </Select>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Quantity" htmlFor="qty" required error={errors.qty}>
                <Input id="qty" type="number" min="1" step="1" mono placeholder="0"
                  value={qty} onChange={(e) => setQty(e.target.value)} invalid={!!errors.qty} />
              </Field>
              <Field label={orderType === 'LIMIT' ? 'Limit Price' : 'Market Price'} htmlFor="price" error={errors.limitPrice}>
                <Input id="price" type="number" min="0" step="0.01" mono
                  value={orderType === 'LIMIT' ? limitPrice : formatNum(price)}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  disabled={orderType === 'MARKET'} invalid={!!errors.limitPrice} />
              </Field>
            </div>

            {serverError && (
              <div className="rounded-md border border-bear/30 bg-bear-soft px-3 py-2 text-sm text-bear">
                {serverError}
              </div>
            )}

            <Button type="submit" variant={side === 'BUY' ? 'bull' : 'bear'} size="lg" className="w-full" disabled={!canSubmit || busy}>
              {busy ? 'Placing...' : `${side === 'BUY' ? 'Buy' : 'Sell'} ${symbol}`}
            </Button>
          </form>
        </CardBody>
      </Card>

      <div className="space-y-5">
        <Card>
          <CardHeader title="Order Summary" />
          <CardBody className="space-y-3 text-sm">
            <Row label="Side"><Badge tone={side === 'BUY' ? 'bull' : 'bear'}>{side}</Badge></Row>
            <Row label="Est. Price" mono>{formatNum(price)}</Row>
            <Row label="Quantity" mono>{qtyNum || '--'}</Row>
            <Row label="Subtotal" mono>{formatNPR(subtotal)}</Row>
            <Row label="Fees (0.36%)" mono>{formatNPR(fee)}</Row>
            <div className="border-t border-line pt-3">
              <Row label="Total" mono bold>{formatNPR(total)}</Row>
            </div>
            <Row label="Cash Available" mono>{formatNPR(cash)}</Row>
          </CardBody>
        </Card>

        {confirmed && (
          <Card className="border-bull/40 bg-bull-soft">
            <CardBody className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 text-bull" size={20} />
              <div className="text-sm">
                <p className="font-semibold text-ink">Order executed (simulated)</p>
                <p className="mt-1 text-ink-2">
                  {confirmed.side} {confirmed.qty} {confirmed.symbol} @ {formatNum(confirmed.price)}
                </p>
                <p className="mt-1 font-mono text-xs text-ink-3">{confirmed.id}</p>
              </div>
            </CardBody>
          </Card>
        )}
      </div>
    </div>
  )
}

function Row({ label, children, mono, bold }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-ink-3">{label}</span>
      <span className={cn(mono && 'font-mono tabular-nums', bold ? 'font-semibold text-ink' : 'text-ink-2')}>
        {children}
      </span>
    </div>
  )
}
