import { useState } from 'react'
import { IconNews, IconTrash } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import { confirm } from '@/components/admin/confirm'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { countOf, formatDate, inputCls, notifyError } from '@/components/admin/helpers'

export default function AdminNewsletter() {
  const [q, setQ] = useState('')
  const [active, setActive] = useState('true')
  const [busy, setBusy] = useState(null)
  const list = useAdminList('/admin/newsletter', 'subscribers', { q, active }, { perPage: 50 })

  const remove = async (subscriber) => {
    const sure = await confirm({
      title: 'Remove this subscriber?',
      message: `${subscriber.email} is deleted from the list and will stop receiving the newsletter.`,
      confirmLabel: 'Remove',
      danger: true,
    })
    if (!sure) return
    setBusy(subscriber.id)
    try {
      await adminApi.delete(`/admin/newsletter/${subscriber.id}`)
      toast.success('Subscriber removed.')
      list.reload()
    } catch (err) {
      notifyError(err, 'Could not remove this subscriber.')
    }
    setBusy(null)
  }

  return (
    <div>
      <PageHeading title="Newsletter" subtitle={`${countOf(list.total, 'subscribers')} found`} />

      <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Search by email" />
        <select value={active} onChange={(e) => setActive(e.target.value)} aria-label="Subscription" className={`${inputCls} w-auto`}>
          <option value="true">Subscribed</option>
          <option value="false">Including unsubscribed</option>
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={Boolean(q)}
        skeleton={<TableSkeleton rows={8} columns={3} />}
        emptyIcon={IconNews}
        emptyTitle="No subscribers yet"
        emptyHint="People who sign up from the home page will appear here."
      >
        <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white ${list.loading ? 'opacity-60' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Email</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Subscribed</th>
                <th className="px-6 py-3 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {list.rows.map((s) => (
                <tr key={s.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                  <td className="px-6 py-3 text-gray-900">{s.email}</td>
                  <td className="px-6 py-3">
                    <Badge tone={s.is_active ? 'green' : 'gray'}>{s.is_active ? 'Subscribed' : 'Unsubscribed'}</Badge>
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-gray-500">{formatDate(s.subscribed_at)}</td>
                  <td className="px-6 py-3 text-right">
                    <button
                      type="button" onClick={() => remove(s)} disabled={busy === s.id}
                      aria-label={`Remove ${s.email}`}
                      className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      <IconTrash size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="subscribers" />
      </DataState>
    </div>
  )
}
