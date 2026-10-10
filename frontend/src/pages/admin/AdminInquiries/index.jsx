import { useState } from 'react'
import { IconBuildingStore } from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { toast } from '@/components/ui/Toast'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { formatDate, humanize, inputCls, notifyError } from '@/components/admin/helpers'

const STATUSES = ['new', 'contacted', 'qualified', 'converted', 'rejected']
const TONE = { new: 'amber', contacted: 'blue', qualified: 'purple', converted: 'green', rejected: 'red' }
const VOLUME = {
  below_10k: 'Below ₹10,000 / month', '10k_50k': '₹10,000 – ₹50,000 / month',
  '50k_1lac': '₹50,000 – ₹1 lakh / month', above_1lac: 'Above ₹1 lakh / month',
}

function InquiryCard({ inquiry, onChanged }) {
  const [notes, setNotes] = useState(inquiry.notes || '')
  const [busy, setBusy] = useState(false)

  const save = async (patch, message) => {
    setBusy(true)
    try {
      await adminApi.patch(`/admin/wholesale-inquiries/${inquiry.id}`, { status: inquiry.status, ...patch })
      toast.success(message)
      onChanged()
    } catch (err) {
      notifyError(err, 'Could not update this inquiry.')
    }
    setBusy(false)
  }

  return (
    <li className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium text-gray-900">{inquiry.shop_name}</div>
          <div className="text-sm text-gray-600">{inquiry.owner_name} · {inquiry.city}, {inquiry.state}</div>
          <div className="mt-1 flex flex-wrap gap-x-4 text-sm">
            <a href={`tel:${inquiry.phone}`} className="text-gray-900 hover:underline">{inquiry.phone}</a>
            <a href={`mailto:${inquiry.email}`} className="text-gray-900 hover:underline">{inquiry.email}</a>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={TONE[inquiry.status]}>{humanize(inquiry.status)}</Badge>
          <select
            value={inquiry.status} disabled={busy} aria-label="Change status"
            onChange={(e) => save({ status: e.target.value }, `Marked ${e.target.value}.`)}
            className={`${inputCls} w-auto py-1.5 text-xs`}
          >
            {STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
          </select>
        </div>
      </div>

      <dl className="mt-4 grid gap-x-6 gap-y-2 border-t border-gray-100 pt-4 text-sm sm:grid-cols-3">
        <div><dt className="text-xs text-gray-500">Monthly volume</dt><dd className="text-gray-900">{VOLUME[inquiry.monthly_volume_range] || humanize(inquiry.monthly_volume_range)}</dd></div>
        <div><dt className="text-xs text-gray-500">GST number</dt><dd className="text-gray-900">{inquiry.gst_number || '—'}</dd></div>
        <div><dt className="text-xs text-gray-500">Received</dt><dd className="text-gray-900">{formatDate(inquiry.submitted_at)}</dd></div>
        {inquiry.categories_interest?.length > 0 && (
          <div className="sm:col-span-3"><dt className="text-xs text-gray-500">Interested in</dt><dd className="text-gray-900">{inquiry.categories_interest.join(', ')}</dd></div>
        )}
      </dl>

      <div className="mt-4">
        <label htmlFor={`notes-${inquiry.id}`} className="text-xs text-gray-500">Internal notes</label>
        <div className="mt-1 flex gap-2">
          <textarea
            id={`notes-${inquiry.id}`} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="Called on Monday, sending the catalogue…" className={inputCls}
          />
          <button
            type="button" disabled={busy || notes === (inquiry.notes || '')}
            onClick={() => save({ notes }, 'Notes saved.')}
            className="self-start rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </div>
    </li>
  )
}

export default function AdminInquiries() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const list = useAdminList('/admin/wholesale-inquiries', 'inquiries', { q, status })

  return (
    <div>
      <PageHeading title="Wholesale inquiries" subtitle={`${list.total.toLocaleString('en-IN')} matching inquiries`} />

      <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Shop, owner, email, phone or city" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status" className={`${inputCls} w-auto`}>
          <option value="">All statuses</option>
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
        emptyIcon={IconBuildingStore}
        emptyTitle="No wholesale inquiries yet"
        emptyHint="Requests from the Wholesale page will appear here."
      >
        <ul className={`space-y-3 ${list.loading ? 'opacity-60' : ''}`}>
          {list.rows.map((i) => <InquiryCard key={`${i.id}-${i.status}-${i.notes}`} inquiry={i} onChanged={list.reload} />)}
        </ul>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="inquiries" />
      </DataState>
    </div>
  )
}
