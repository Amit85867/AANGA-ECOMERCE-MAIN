import { Fragment, useState } from 'react'
import { IconChevronDown, IconChevronRight, IconHistory } from '@tabler/icons-react'
import DataState, { TableSkeleton } from '@/components/admin/DataState'
import Pagination from '@/components/admin/Pagination'
import useAdminList from '@/components/admin/useAdminList'
import { Badge, PageHeading, SearchInput } from '@/components/admin/controls'
import { formatDateTime, humanize, inputCls } from '@/components/admin/helpers'

const ACTOR_TONE = { admin: 'blue', customer: 'purple', system: 'gray', anonymous: 'red' }

const hasDetail = (changes) => changes && Object.keys(changes).length > 0

export default function AdminAuditLog() {
  const [q, setQ] = useState('')
  const [entityType, setEntityType] = useState('')
  const [actorType, setActorType] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [open, setOpen] = useState(null)

  const list = useAdminList(
    '/admin/audit-log', 'entries',
    { q, entity_type: entityType, actor_type: actorType, from, to },
    { perPage: 25 },
  )
  const entityTypes = list.extra.entity_types || []

  return (
    <div>
      <PageHeading
        title="Audit log"
        subtitle="Every change made in the admin panel, every refund and every admin sign-in, with who made it."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto]">
        <SearchInput value={q} onChange={setQ} placeholder="Search summary, action, admin or record id" />
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)} aria-label="Area" className={`${inputCls} w-auto`}>
          <option value="">All areas</option>
          {entityTypes.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
        </select>
        <select value={actorType} onChange={(e) => setActorType(e.target.value)} aria-label="Made by" className={`${inputCls} w-auto`}>
          <option value="">Anyone</option>
          <option value="admin">Admins</option>
          <option value="customer">Customers</option>
          <option value="system">System</option>
          <option value="anonymous">Not signed in</option>
        </select>
        <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} aria-label="From date" className={`${inputCls} w-auto`} />
        <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} aria-label="To date" className={`${inputCls} w-auto`} />
      </div>

      <DataState
        loading={list.loading && list.rows.length === 0}
        error={list.error}
        onRetry={list.reload}
        empty={list.rows.length === 0}
        filtered={list.filtered}
        skeleton={<TableSkeleton rows={8} columns={5} />}
        emptyIcon={IconHistory}
        emptyTitle="Nothing recorded yet"
        emptyHint="Changes made in the admin panel will appear here."
      >
        <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white ${list.loading ? 'opacity-60' : ''}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="w-8 px-3 py-3" />
                <th className="px-3 py-3 font-medium">When</th>
                <th className="px-3 py-3 font-medium">Who</th>
                <th className="px-3 py-3 font-medium">Area</th>
                <th className="px-3 py-3 font-medium">What happened</th>
              </tr>
            </thead>
            <tbody>
              {list.rows.map((e) => {
                const expandable = hasDetail(e.changes)
                const isOpen = open === e.id
                return (
                  <Fragment key={e.id}>
                    <tr className="border-b border-gray-50 align-top last:border-0">
                      <td className="px-3 py-3">
                        {expandable && (
                          <button
                            type="button"
                            aria-expanded={isOpen}
                            aria-label={isOpen ? 'Hide details' : 'Show details'}
                            onClick={() => setOpen(isOpen ? null : e.id)}
                            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                          >
                            {isOpen ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
                          </button>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-gray-500">{formatDateTime(e.created_at)}</td>
                      <td className="px-3 py-3">
                        <div className="text-gray-900">{e.actor}</div>
                        <Badge tone={ACTOR_TONE[e.actor_type]}>{humanize(e.actor_type)}</Badge>
                      </td>
                      <td className="px-3 py-3 text-gray-600">
                        {humanize(e.entity_type)}
                        {e.entity_id && <span className="text-gray-400"> #{e.entity_id}</span>}
                      </td>
                      <td className="px-3 py-3">
                        <div className="text-gray-900">{e.summary || humanize(e.action)}</div>
                        {e.summary && <div className="text-xs text-gray-400">{e.action}</div>}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="border-b border-gray-50 bg-gray-50">
                        <td />
                        <td colSpan={4} className="px-3 pb-4 pt-1">
                          <pre className="max-h-72 overflow-auto rounded-lg bg-white p-3 text-xs leading-relaxed text-gray-700 ring-1 ring-gray-200">
                            {JSON.stringify(e.changes, null, 2)}
                          </pre>
                          {e.ip && <p className="mt-2 text-xs text-gray-400">From {e.ip}</p>}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
        <Pagination page={list.page} pages={list.pages} total={list.total} onChange={list.setPage} noun="entries" />
      </DataState>
    </div>
  )
}
