import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconUsers } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { countOf, formatDate, humanize, inputCls, notifyError } from '@/components/admin/helpers'

export default function AdminUsers() {
  const [q, setQ] = useState('')
  const [accountType, setAccountType] = useState('')
  const [active, setActive] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [busy, setBusy] = useState(null)
  const [exporting, setExporting] = useState(false)

  const [sortBy, dir] = sort.split(':')
  const list = useAdminList('/admin/users', 'users', {
    q, account_type: accountType, active, sort: sortBy, dir,
  })

  const toggleActive = async (user) => {
    // Blocking locks a real person out of their account, so it is confirmed;
    // unblocking is harmless and is not.
    if (user.is_active) {
      const sure = await confirm({
        title: `Block ${user.full_name}?`,
        message: 'They will be signed out and unable to sign in or place orders until you unblock them. Their past orders are kept.',
        confirmLabel: 'Block customer',
        danger: true,
      })
      if (!sure) return
    }
    setBusy(user.id)
    try {
      await adminApi.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
      toast.success(user.is_active ? `${user.full_name} blocked.` : `${user.full_name} unblocked.`)
      list.reload()
    } catch (err) {
      notifyError(err, 'Could not update this customer.')
    }
    setBusy(null)
  }

  // The list as filtered right now, as a spreadsheet. Names, contact
  // details and order totals only — never passwords or payment details.
  const exportCsv = async () => {
    setExporting(true)
    try {
      const { data } = await adminApi.get('/admin/users/export.csv', {
        params: { q: q || undefined, account_type: accountType || undefined, active: active || undefined },
        responseType: 'blob',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(data)
      link.download = `customers-${new Date().toISOString().slice(0, 10)}.csv`
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (err) {
      notifyError(err, 'Could not export the customer list.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div>
      <PageHeading title="Customers" subtitle={`${countOf(list.total, 'customers')} found`}>
        <button
          type="button" disabled={exporting} onClick={exportCsv}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          {exporting ? 'Preparing…' : 'Export CSV'}
        </button>
      </PageHeading>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Name, email or phone" />
        <select value={accountType} onChange={(e) => setAccountType(e.target.value)} aria-label="Account type" className={`${inputCls} w-auto`}>
          <option value="">Retail and wholesale</option>
          <option value="retail">Retail</option>
          <option value="wholesale">Wholesale</option>
        </select>
        <select value={active} onChange={(e) => setActive(e.target.value)} aria-label="Status" className={`${inputCls} w-auto`}>
          <option value="">Active and blocked</option>
          <option value="true">Active</option>
          <option value="false">Blocked</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputCls} w-auto`}>
          <option value="created_at:desc">Newest first</option>
          <option value="created_at:asc">Oldest first</option>
          <option value="full_name:asc">Name A–Z</option>
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={list.filtered && Boolean(q || accountType || active)}
        skeleton={<TableSkeleton rows={8} columns={6} />}
        emptyIcon={IconUsers}
        emptyTitle="No customers yet"
        emptyHint="Customers appear here when they create an account."
      >
        <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white ${list.loading ? 'opacity-60' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Customer</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Signs in with</th>
                <th className="px-6 py-3 text-right font-medium">Orders</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Joined</th>
                <th className="relative px-6 py-3 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {list.rows.map((u) => (
                <tr key={u.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <Link to={`/admin/users/${u.id}`} className="font-medium text-gray-900 hover:underline">
                      {u.full_name}
                    </Link>
                    <div className="text-xs text-gray-500">{u.email}{u.phone ? ` · ${u.phone}` : ''}</div>
                  </td>
                  <td className="px-6 py-3">
                    <Badge tone={u.account_type === 'wholesale' ? 'purple' : 'gray'}>{humanize(u.account_type)}</Badge>
                  </td>
                  <td className="px-6 py-3 text-gray-600">{humanize(u.auth_provider)}</td>
                  <td className="px-6 py-3 text-right tabular-nums text-gray-900">{u.order_count}</td>
                  <td className="px-6 py-3">
                    <Badge tone={u.is_active ? 'green' : 'red'}>{u.is_active ? 'Active' : 'Blocked'}</Badge>
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-gray-500">{formatDate(u.created_at)}</td>
                  <td className="px-6 py-3 text-right">
                    <button
                      type="button" onClick={() => toggleActive(u)} disabled={busy === u.id}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
                        u.is_active ? 'text-red-700 hover:bg-red-50' : 'text-green-700 hover:bg-green-50'
                      }`}
                    >
                      {busy === u.id ? 'Saving…' : u.is_active ? 'Block' : 'Unblock'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="customers" />
      </DataState>
    </div>
  )
}
