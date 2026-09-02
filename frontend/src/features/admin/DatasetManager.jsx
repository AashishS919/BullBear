import { useState } from 'react'
import { UploadCloud, RefreshCw, Trash2 } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { formatInt, formatDate } from '../../lib/format'
import { Card, CardHeader, CardBody } from '../../components/ui/Card'
import { Field, Input, Select } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Table, THead, TBody, TR, TH, TD } from '../../components/ui/Table'
import { Loader, ErrorState } from '../../components/ui/State'

export function DatasetManager() {
  const datasets = useApi(() => api.adminDatasets(), [])
  const tickers = useApi(() => api.tickers(), [])

  const [symbol, setSymbol] = useState('NABIL')
  const [source, setSource] = useState('CSV')
  const [fileName, setFileName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function createDataset(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      await api.createDataset({ symbol, source })
      setFileName('')
      datasets.reload()
    } catch (e2) {
      setErr(e2.message || 'Failed to create dataset.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id) {
    try {
      await api.deleteDataset(id)
      datasets.reload()
    } catch (e2) {
      setErr(e2.message || 'Failed to delete.')
    }
  }

  if (datasets.loading) return <Loader />
  if (datasets.error) return <ErrorState error={datasets.error} onRetry={datasets.reload} />

  const rows = datasets.data || []
  const tickerList = tickers.data || [{ symbol: 'NABIL' }]

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader title="Tracked Datasets" subtitle="5-year OHLCV history per ticker" />
        <Table>
          <THead>
            <TR>
              <TH>Dataset</TH>
              <TH>Symbol</TH>
              <TH align="right">Rows</TH>
              <TH>Coverage</TH>
              <TH align="center">Source</TH>
              <TH align="center">Status</TH>
              <TH align="right">Actions</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((d) => (
              <TR key={d.id}>
                <TD mono className="text-xs">{d.id}</TD>
                <TD className="font-mono font-semibold">{d.symbol}</TD>
                <TD align="right" mono>{formatInt(d.rows)}</TD>
                <TD className="text-xs text-ink-2">{formatDate(d.from)} - {formatDate(d.to)}</TD>
                <TD align="center"><Badge tone="neutral">{d.source}</Badge></TD>
                <TD align="center"><Badge status={d.status} /></TD>
                <TD align="right">
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" aria-label="Re-sync" onClick={datasets.reload}>
                      <RefreshCw size={15} />
                    </Button>
                    <Button variant="ghost" size="sm" aria-label="Delete" className="text-bear" onClick={() => remove(d.id)}>
                      <Trash2 size={15} />
                    </Button>
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>

      <Card className="self-start">
        <CardHeader title="Register Dataset" />
        <CardBody>
          <form className="space-y-4" onSubmit={createDataset}>
            <Field label="Ticker" htmlFor="ds-symbol" required>
              <Select id="ds-symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                {tickerList.map((t) => <option key={t.symbol} value={t.symbol}>{t.symbol}</option>)}
              </Select>
            </Field>

            <Field label="Source" htmlFor="ds-source">
              <Select id="ds-source" value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="CSV">CSV Upload</option>
                <option value="API">NEPSE API Pull</option>
              </Select>
            </Field>

            {source === 'CSV' && (
              <Field label="CSV File" hint="Columns: date, open, high, low, close, volume">
                <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-line-2 bg-surface-2 px-4 py-6 text-center hover:border-accent">
                  <UploadCloud size={22} className="text-ink-3" />
                  <span className="text-sm text-ink-2">{fileName || 'Click to select a .csv file'}</span>
                  <input type="file" accept=".csv" className="hidden"
                    onChange={(e) => setFileName(e.target.files?.[0]?.name ?? '')} />
                </label>
              </Field>
            )}

            {err && (
              <div className="rounded-md border border-bear/30 bg-bear-soft px-3 py-2 text-sm text-bear">{err}</div>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={busy}>
              {busy ? 'Registering...' : 'Register Dataset'}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
