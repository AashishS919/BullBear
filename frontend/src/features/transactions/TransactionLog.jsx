import { useState } from 'react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { formatNPR, formatNum, formatDate } from '../../lib/format'
import { Card, CardHeader } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Select } from '../../components/ui/Input'
import { Table, THead, TBody, TR, TH, TD } from '../../components/ui/Table'
import { Loader, ErrorState, EmptyState } from '../../components/ui/State'

const FILTERS = ['ALL', 'BUY', 'SELL']

export function TransactionLog() {
  const [filter, setFilter] = useState('ALL')
  const { data, loading, error, reload } = useApi(
    () => api.transactions(filter === 'ALL' ? undefined : filter),
    [filter],
  )

  const rows = data || []

  return (
    <Card>
      <CardHeader
        title="Transaction History"
        subtitle="Order and execution log"
        action={
          <Select value={filter} onChange={(e) => setFilter(e.target.value)} className="w-32">
            {FILTERS.map((f) => <option key={f} value={f}>{f}</option>)}
          </Select>
        }
      />
      {loading ? (
        <Loader />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState message="No transactions yet." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Order ID</TH>
              <TH>Date</TH>
              <TH>Symbol</TH>
              <TH align="center">Side</TH>
              <TH align="right">Qty</TH>
              <TH align="right">Price</TH>
              <TH align="right">Value</TH>
              <TH align="center">Status</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((t) => (
              <TR key={t.id}>
                <TD mono className="text-xs">{t.id}</TD>
                <TD>{formatDate(t.date)}</TD>
                <TD mono className="font-semibold">{t.symbol}</TD>
                <TD align="center"><Badge tone={t.side === 'BUY' ? 'bull' : 'bear'}>{t.side}</Badge></TD>
                <TD align="right" mono>{t.qty}</TD>
                <TD align="right" mono>{formatNum(t.price)}</TD>
                <TD align="right" mono>{formatNPR(t.qty * t.price)}</TD>
                <TD align="center"><Badge status={t.status} /></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </Card>
  )
}
