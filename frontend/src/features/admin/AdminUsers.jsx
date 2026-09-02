import { useMemo, useState } from 'react'
import { Users, Activity, ShieldCheck, UserX } from 'lucide-react'
import { api } from '../../lib/api'
import { useApi } from '../../hooks/useApi'
import { formatDate } from '../../lib/format'
import { Card, CardHeader } from '../../components/ui/Card'
import { StatTile } from '../../components/ui/StatTile'
import { Badge } from '../../components/ui/Badge'
import { Input, Select } from '../../components/ui/Input'
import { Table, THead, TBody, TR, TH, TD } from '../../components/ui/Table'
import { Loader, ErrorState } from '../../components/ui/State'

export function AdminUsers() {
  const { data, loading, error, reload } = useApi(() => api.adminUsers(), [])
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('ALL')

  const all = data || []
  const rows = useMemo(() => {
    return all.filter((u) => {
      const matchQ = !query ||
        u.name.toLowerCase().includes(query.toLowerCase()) ||
        u.email.toLowerCase().includes(query.toLowerCase())
      const matchR = role === 'ALL' || u.role === role
      return matchQ && matchR
    })
  }, [all, query, role])

  if (loading) return <Loader />
  if (error) return <ErrorState error={error} onRetry={reload} />

  const active = all.filter((u) => u.status === 'ACTIVE').length
  const admins = all.filter((u) => u.role === 'ADMIN').length
  const suspended = all.filter((u) => u.status === 'SUSPENDED').length

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Total Users" value={all.length} icon={Users} />
        <StatTile label="Active" value={active} icon={Activity} />
        <StatTile label="Admins" value={admins} icon={ShieldCheck} />
        <StatTile label="Suspended" value={suspended} icon={UserX} />
      </div>

      <Card>
        <CardHeader
          title="Users"
          subtitle="Monitor accounts and activity"
          action={
            <div className="flex gap-2">
              <Input placeholder="Search name or email" value={query}
                onChange={(e) => setQuery(e.target.value)} className="w-56" />
              <Select value={role} onChange={(e) => setRole(e.target.value)} className="w-32">
                <option value="ALL">All Roles</option>
                <option value="ADMIN">Admin</option>
                <option value="USER">User</option>
              </Select>
            </div>
          }
        />
        <Table>
          <THead>
            <TR>
              <TH>User ID</TH>
              <TH>Name</TH>
              <TH>Email</TH>
              <TH align="center">Role</TH>
              <TH align="center">Status</TH>
              <TH>Joined</TH>
              <TH>Last Seen</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((u) => (
              <TR key={u.id}>
                <TD mono className="text-xs">{u.id}</TD>
                <TD className="font-medium">{u.name}</TD>
                <TD className="text-ink-2">{u.email}</TD>
                <TD align="center"><Badge tone={u.role === 'ADMIN' ? 'accent' : 'neutral'}>{u.role}</Badge></TD>
                <TD align="center"><Badge status={u.status} /></TD>
                <TD>{formatDate(u.joined)}</TD>
                <TD>{formatDate(u.last_seen)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>
    </div>
  )
}
