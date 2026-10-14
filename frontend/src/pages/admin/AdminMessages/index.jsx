import { useState } from 'react'
import { IconMail } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/toastStore'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { formatDateTime, humanize, inputCls, notifyError } from '@/components/admin/helpers'

const STATUSES = ['unread', 'read', 'replied', 'closed']
const TONE = { unread: 'amber', read: 'blue', replied: 'green', closed: 'gray' }

export default function AdminMessages() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(null)
  const list = useAdminList('/admin/contact-messages', 'messages', { q, status })

  const setMessageStatus = async (message, next) => {
    setBusy(message.id)
    try {
      await adminApi.patch(`/admin/contact-messages/${message.id}`, { status: next })
      toast.success(`Marked ${next}.`)
      list.reload()
    } catch (err) {
      notifyError(err, 'Could not update this message.')
    }
    setBusy(null)
  }

  return (
    <div>
      <PageHeading title="Messages" subtitle="Sent from the Contact page." />

      <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Name, email or message text" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status" className={`${inputCls} w-auto`}>
          <option value="">All messages</option>
          {STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={list.filtered}
        skeleton={<TableSkeleton rows={4} columns={4} />}
        emptyIcon={IconMail}
        emptyTitle="No messages yet"
        emptyHint="Messages from the Contact page will appear here."
      >
        <ul className={`space-y-3 ${list.loading ? 'opacity-60' : ''}`}>
          {list.rows.map((m) => (
            <li
              key={m.id}
              className={`rounded-xl border bg-white p-5 ${m.status === 'unread' ? 'border-amber-300' : 'border-gray-200'}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium text-gray-900">{m.name}</div>
                  <div className="flex flex-wrap gap-x-4 text-sm">
                    <a href={`mailto:${m.email}?subject=${encodeURIComponent(`Re: your message to AANGA`)}`} className="text-gray-900 hover:underline">{m.email}</a>
                    {m.phone && <a href={`tel:${m.phone}`} className="text-gray-900 hover:underline">{m.phone}</a>}
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{humanize(m.subject)} · {formatDateTime(m.sent_at)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={TONE[m.status]}>{humanize(m.status)}</Badge>
                  <select
                    value={m.status} disabled={busy === m.id} aria-label="Change status"
                    onChange={(e) => setMessageStatus(m, e.target.value)}
                    className={`${inputCls} w-auto py-1.5 text-xs`}
                  >
                    {STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
                  </select>
                </div>
              </div>
              <p className="mt-3 whitespace-pre-line border-t border-gray-100 pt-3 text-sm leading-relaxed text-gray-800">
                {m.message}
              </p>
            </li>
          ))}
        </ul>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="messages" />
      </DataState>
    </div>
  )
}
