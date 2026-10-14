import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  IconArrowLeft, IconCalendarEvent, IconEye, IconPlayerStop, IconPlus, IconTrash,
} from '@tabler/icons-react'
import adminApi from '@/services/adminApi'
import { EmptyState, ErrorState, CardSkeleton, TableSkeleton } from '@/components/admin/DataState'
import { Badge, PageHeading } from '@/components/admin/controls'
import { confirm } from '@/components/admin/confirm'
import { inputCls, notifyError } from '@/components/admin/helpers'
import { Field, ImageField, Toggle } from '@/components/admin/kit'
import {
  btnDanger, btnGhost, btnPrimary, cardCls, fieldErrors, formatIst, fromIstInput, toIstInput, useLoad,
} from '@/components/admin/kitUtils'
import { toast } from '@/components/ui/toastStore'

const STATUS = {
  live: ['green', 'Live now'],
  scheduled: ['blue', 'Scheduled'],
  ended: ['gray', 'Ended'],
}

async function openPreview(campaign) {
  // Opened straight away, while this is still "the click": a window opened
  // after waiting for the server is treated as a pop-up and blocked.
  const tab = window.open('', '_blank')
  try {
    const { data } = await adminApi.post(`/admin/campaigns/${campaign.id}/preview`)
    if (tab) {
      tab.opener = null
      tab.location = data.path
    } else {
      window.location.assign(data.path)
    }
  } catch (err) {
    tab?.close()
    notifyError(err, 'Could not open the preview.')
  }
}

async function endNow(campaign, after) {
  if (!(await confirm({
    title: `End “${campaign.name}” now?`, confirmLabel: 'End now', danger: true,
    message: 'The store goes back to normal straight away: sale prices, the festive look, the campaign’s slides and its coupons all stop.',
  }))) return
  try {
    await adminApi.post(`/admin/campaigns/${campaign.id}/end`)
    toast.success('Campaign ended. The store is back to normal.')
    after()
  } catch (err) {
    notifyError(err, 'Could not end this campaign.')
  }
}

function CampaignList() {
  const { data, loading, error, reload } = useLoad('/admin/campaigns')
  const rows = data?.campaigns || []

  const remove = async (c) => {
    if (!(await confirm({
      title: `Delete “${c.name}”?`, confirmLabel: 'Delete', danger: true,
      message: 'Its slides and promo banners are deleted with it. Its coupons are switched off.',
    }))) return
    try {
      await adminApi.delete(`/admin/campaigns/${c.id}`)
      toast.success('Deleted.')
      reload()
    } catch (err) {
      notifyError(err, 'Could not delete this campaign.')
    }
  }

  return (
    <div>
      <PageHeading title="Campaigns" subtitle="Festivals and sales that switch themselves on and off at the times you set. One runs at a time.">
        <Link to="/admin/campaigns/new" className={btnPrimary}><IconPlus size={18} /> New campaign</Link>
      </PageHeading>
      {loading && !data ? <TableSkeleton rows={3} columns={4} /> : error ? <ErrorState message={error} onRetry={reload} /> : rows.length === 0 ? (
        <EmptyState icon={IconCalendarEvent} title="No campaigns yet" hint="Plan a festival or a sale: an announcement, hero slides, a collection on sale, coupons and a festive look, all on one schedule." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500">
                <th className="px-6 py-3 font-medium">Campaign</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Runs</th>
                <th className="px-6 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3">
                    <Link to={`/admin/campaigns/${c.id}`} className="font-medium text-gray-900 hover:underline">{c.name}</Link>
                    {c.is_demo && <span className="ml-2"><Badge tone="purple">Demo</Badge></span>}
                    <div className="text-xs text-gray-500">
                      {[c.collection_name && `Collection: ${c.collection_name}`, c.sale_percent && `${c.sale_percent}% off`, c.decoration_enabled && 'Festive look'].filter(Boolean).join(' · ') || 'No extras'}
                    </div>
                  </td>
                  <td className="px-6 py-3"><Badge tone={STATUS[c.status][0]}>{STATUS[c.status][1]}</Badge></td>
                  <td className="px-6 py-3 text-gray-600">
                    <div>{formatIst(c.starts_at)}</div>
                    <div className="text-xs text-gray-500">to {formatIst(c.ended_at || c.ends_at)}{c.ended_at ? ' (ended early)' : ''}</div>
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex flex-wrap justify-end gap-1">
                      {c.status !== 'ended' && <button type="button" className={`${btnGhost} px-3 py-1.5`} onClick={() => openPreview(c)}><IconEye size={16} /> Preview</button>}
                      {c.status === 'live' && <button type="button" className={`${btnDanger} px-3 py-1.5`} onClick={() => endNow(c, reload)}><IconPlayerStop size={16} /> End now</button>}
                      <Link to={`/admin/campaigns/${c.id}`} className={`${btnGhost} px-3 py-1.5`}>Edit</Link>
                      {c.status !== 'live' && (
                        <button type="button" onClick={() => remove(c)} aria-label={`Delete ${c.name}`} title="Delete" className="rounded p-2 text-gray-500 hover:bg-red-50 hover:text-red-600"><IconTrash size={17} /></button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* Hero slides and promo banners that belong to this campaign. */
function Attachments({ campaign, kind, title, hint, onChange }) {
  const isSlide = kind === 'banners'
  const items = isSlide ? campaign.slides : campaign.promo_banners
  const empty = {
    title: '', subtitle: '', description: '', image_url: '',
    link_text: campaign.collection_slug ? `Shop the ${campaign.collection_name}` : 'Shop now',
    link_url: campaign.collection_slug ? `/collections/${campaign.collection_slug}` : '/shop',
  }
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)

  const add = async (e) => {
    e.preventDefault()
    if (saving) return
    if (isSlide && !form.image_url) { toast.error('Choose a picture for the slide.'); return }
    setSaving(true)
    try {
      await adminApi.post(`/admin/${kind}`, {
        ...form, subtitle: form.subtitle || null, description: form.description || null,
        image_url: form.image_url || null, campaign_id: campaign.id, sort_order: items.length, is_active: true,
      })
      toast.success('Added.')
      setForm(null)
      onChange()
    } catch (err) {
      notifyError(err, 'Could not add this.')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (item) => {
    if (!(await confirm({ title: `Remove “${item.title}”?`, confirmLabel: 'Remove', danger: true }))) return
    try {
      await adminApi.delete(`/admin/${kind}/${item.id}`)
      onChange()
    } catch (err) {
      notifyError(err, 'Could not remove this.')
    }
  }

  return (
    <section className={cardCls} aria-label={title}>
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="font-medium text-gray-900">{title} ({items.length})</h2>
        {!form && <button type="button" className={`${btnGhost} px-3 py-1.5`} onClick={() => setForm(empty)}><IconPlus size={16} /> Add</button>}
      </div>
      <p className="mb-4 text-xs text-gray-500">{hint}</p>

      {items.length > 0 && (
        <ul className="mb-4 divide-y divide-gray-100">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-2">
              <div className="h-12 w-16 shrink-0 overflow-hidden rounded bg-gray-100">
                {item.image_url && <img src={item.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm text-gray-900">{item.title}</div>
                {item.link_url && <div className="truncate text-xs text-gray-500">Button: {item.link_text} → {item.link_url}</div>}
              </div>
              <button type="button" onClick={() => remove(item)} aria-label={`Remove ${item.title}`} title="Remove" className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600"><IconTrash size={16} /></button>
            </li>
          ))}
        </ul>
      )}

      {form && (
        <form onSubmit={add} className="space-y-3 rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Headline *"><input required maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className={inputCls} /></Field>
            <Field label="Small line above it"><input maxLength={80} value={form.subtitle} onChange={(e) => setForm({ ...form, subtitle: e.target.value })} className={inputCls} /></Field>
          </div>
          <Field label="Text under the headline"><textarea rows={2} maxLength={300} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inputCls} /></Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Button text"><input maxLength={40} value={form.link_text} onChange={(e) => setForm({ ...form, link_text: e.target.value })} className={inputCls} /></Field>
            <Field label="Button goes to"><input maxLength={300} value={form.link_url} onChange={(e) => setForm({ ...form, link_url: e.target.value })} className={inputCls} /></Field>
          </div>
          <ImageField label={isSlide ? 'Picture *' : 'Picture'} value={form.image_url} onChange={(url) => setForm({ ...form, image_url: url })} help={isSlide ? 'Portrait works best (4:5), at least 960 px wide.' : undefined} />
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Adding…' : 'Add'}</button>
            <button type="button" className={btnGhost} onClick={() => setForm(null)}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}

function Coupons({ campaign, chosen, setChosen }) {
  const { data, reload } = useLoad('/admin/coupons', { per_page: 100 })
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const available = (data?.coupons || []).filter((c) => !c.campaign_id || c.campaign_id === campaign?.id)

  const create = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const { data: coupon } = await adminApi.post('/admin/coupons', {
        code: form.code.toUpperCase().trim(), description: form.description || null,
        discount_type: form.discount_type, discount_value: Number(form.discount_value),
        min_order_value: Number(form.min_order_value || 0),
        usage_limit: form.usage_limit ? Number(form.usage_limit) : null, is_active: true,
      })
      setChosen([...chosen, coupon.id])
      setForm(null)
      toast.success(`${coupon.code} created. Save the campaign to attach it.`)
      reload()
    } catch (err) {
      notifyError(err, Object.values(fieldErrors(err))[0] || 'Could not create this coupon.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className={cardCls} aria-label="Coupons">
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="font-medium text-gray-900">Coupons ({chosen.length})</h2>
        {!form && (
          <button type="button" className={`${btnGhost} px-3 py-1.5`} onClick={() => setForm({ code: '', description: '', discount_type: 'percentage', discount_value: '', min_order_value: '', usage_limit: '' })}>
            <IconPlus size={16} /> New coupon
          </button>
        )}
      </div>
      <p className="mb-4 text-xs text-gray-500">A ticked coupon works only while this campaign is live, and expires when it ends.</p>

      {available.length === 0 && !form && <p className="text-sm text-gray-500">No coupons to attach yet.</p>}
      <ul className="space-y-1">
        {available.map((c) => (
          <li key={c.id}>
            <label className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-gray-50">
              <input
                type="checkbox" className="h-4 w-4 rounded" checked={chosen.includes(c.id)}
                onChange={(e) => setChosen(e.target.checked ? [...chosen, c.id] : chosen.filter((x) => x !== c.id))}
              />
              <span className="font-mono text-sm font-medium text-gray-900">{c.code}</span>
              <span className="text-xs text-gray-500">
                {c.discount_type === 'percentage' ? `${c.discount_value}% off` : `₹${c.discount_value} off`}
                {c.min_order_value > 0 ? ` above ₹${c.min_order_value}` : ''}
                {c.usage_limit ? ` · ${c.used_count}/${c.usage_limit} used` : ''}
              </span>
            </label>
          </li>
        ))}
      </ul>

      {form && (
        <form onSubmit={create} className="mt-4 space-y-3 rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Code *"><input required minLength={3} maxLength={30} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} className={inputCls} /></Field>
            <Field label="Type">
              <select value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value })} className={inputCls}>
                <option value="percentage">Percentage off</option>
                <option value="flat">Rupees off</option>
              </select>
            </Field>
            <Field label={form.discount_type === 'percentage' ? 'Percent *' : 'Rupees *'}>
              <input required type="number" min="1" step="any" value={form.discount_value} onChange={(e) => setForm({ ...form, discount_value: e.target.value })} className={inputCls} />
            </Field>
            <Field label="Minimum order (₹)"><input type="number" min="0" step="any" value={form.min_order_value} onChange={(e) => setForm({ ...form, min_order_value: e.target.value })} className={inputCls} /></Field>
            <Field label="Usage limit" help="How many orders may use it."><input type="number" min="1" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} className={inputCls} /></Field>
            <Field label="Note for yourself"><input maxLength={120} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inputCls} /></Field>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Creating…' : 'Create coupon'}</button>
            <button type="button" className={btnGhost} onClick={() => setForm(null)}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}

const inAWeek = () => new Date(Date.now() + 7 * 86400_000).toISOString()

function CampaignEditor({ id }) {
  const isNew = id === 'new'
  const navigate = useNavigate()
  const { data, loading, error, reload } = useLoad(isNew ? null : `/admin/campaigns/${id}`)
  const meta = useLoad('/admin/campaigns')
  const collections = useLoad('/admin/collections')
  const [form, setForm] = useState(isNew ? {
    name: '', starts_at: toIstInput(new Date().toISOString()), ends_at: toIstInput(inAWeek()),
    announcement_text: '', announcement_highlight: '', announcement_link_text: '', announcement_link_url: '',
    collection_id: '', sale_percent: '', decoration_enabled: false, accent_preset: 'marigold', show_countdown: false,
  } : null)
  const [coupons, setCoupons] = useState([])
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setForm({
      name: data.name, starts_at: toIstInput(data.starts_at), ends_at: toIstInput(data.ends_at),
      announcement_text: data.announcement_text || '', announcement_highlight: data.announcement_highlight || '',
      announcement_link_text: data.announcement_link_text || '', announcement_link_url: data.announcement_link_url || '',
      collection_id: data.collection_id || '', sale_percent: data.sale_percent || '',
      decoration_enabled: data.decoration_enabled, accent_preset: data.accent_preset, show_countdown: data.show_countdown,
    })
    setCoupons(data.coupons.map((c) => c.id))
  }, [data])

  const set = (patch) => setForm((f) => ({ ...f, ...patch }))

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    const body = {
      ...form,
      starts_at: fromIstInput(form.starts_at), ends_at: fromIstInput(form.ends_at),
      collection_id: form.collection_id ? Number(form.collection_id) : null,
      sale_percent: form.sale_percent ? Number(form.sale_percent) : null,
      announcement_text: form.announcement_text || null, announcement_highlight: form.announcement_highlight || null,
      announcement_link_text: form.announcement_link_text || null, announcement_link_url: form.announcement_link_url || null,
      coupon_ids: coupons,
    }
    try {
      if (isNew) {
        const { data: created } = await adminApi.post('/admin/campaigns', body)
        toast.success('Campaign scheduled. Now add its slides.')
        navigate(`/admin/campaigns/${created.id}`, { replace: true })
      } else {
        await adminApi.put(`/admin/campaigns/${id}`, body)
        toast.success('Campaign saved.')
        reload()
      }
      setErrors({})
    } catch (err) {
      const found = fieldErrors(err)
      setErrors(found)
      notifyError(err, found.starts_at || found.ends_at || found.coupon_ids || 'Could not save this campaign.')
    } finally {
      setSaving(false)
    }
  }

  const back = (
    <Link to="/admin/campaigns" className="mb-3 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900">
      <IconArrowLeft size={16} /> All campaigns
    </Link>
  )
  if (!isNew && loading && !data) return <>{back}<CardSkeleton className="h-96" /></>
  if (error) return <>{back}<ErrorState message={error} onRetry={reload} /></>
  if (!form) return null

  const presets = meta.data?.presets || []
  const status = data ? STATUS[data.status] : null

  return (
    <div>
      {back}
      <form onSubmit={save}>
        <PageHeading
          title={isNew ? 'New campaign' : form.name}
          subtitle={isNew ? 'Set the dates first. It goes live and reverts by itself.' : `${formatIst(data.starts_at)} to ${formatIst(data.ended_at || data.ends_at)}`}
        >
          {status && <Badge tone={status[0]}>{status[1]}</Badge>}
          {data && data.status !== 'ended' && <button type="button" className={btnGhost} onClick={() => openPreview(data)}><IconEye size={16} /> Preview</button>}
          {data?.status === 'live' && <button type="button" className={btnDanger} onClick={() => endNow(data, reload)}><IconPlayerStop size={16} /> End now</button>}
          <button type="submit" disabled={saving} className={btnPrimary}>{saving ? 'Saving…' : isNew ? 'Schedule campaign' : 'Save campaign'}</button>
        </PageHeading>

        {data?.status === 'ended' && (
          <p className="mb-6 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600">
            This campaign has ended. To run it again, set new dates and save.
          </p>
        )}

        <div className="grid gap-6 xl:grid-cols-2">
          <section className={`${cardCls} space-y-4`} aria-label="Schedule">
            <h2 className="font-medium text-gray-900">Name and schedule</h2>
            <Field label="Campaign name *" error={errors.name}>
              <input required maxLength={80} value={form.name} onChange={(e) => set({ name: e.target.value })} placeholder="Diwali Festive Sale" className={inputCls} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Starts (Indian time) *" error={errors.starts_at}>
                <input required type="datetime-local" value={form.starts_at} onChange={(e) => set({ starts_at: e.target.value })} className={inputCls} />
              </Field>
              <Field label="Ends (Indian time) *" error={errors.ends_at}>
                <input required type="datetime-local" value={form.ends_at} min={form.starts_at} onChange={(e) => set({ ends_at: e.target.value })} className={inputCls} />
              </Field>
            </div>
            <p className="text-xs text-gray-500">
              Times are always Indian Standard Time. To start straight away, leave the start as it is. Only one campaign can run at a time.
            </p>
          </section>

          <section className={`${cardCls} space-y-4`} aria-label="Announcement bar">
            <h2 className="font-medium text-gray-900">Announcement bar</h2>
            <Field label="Greeting" help="Replaces the usual announcement while the campaign is live." error={errors.announcement_text}>
              <input maxLength={140} value={form.announcement_text} onChange={(e) => set({ announcement_text: e.target.value })} placeholder="Happy Diwali!" className={inputCls} />
            </Field>
            <Field label="Offer (highlighted)" error={errors.announcement_highlight}>
              <input maxLength={140} value={form.announcement_highlight} onChange={(e) => set({ announcement_highlight: e.target.value })} placeholder="Up to 25% off the Diwali Edit" className={inputCls} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Link text" error={errors.announcement_link_text}>
                <input maxLength={40} value={form.announcement_link_text} onChange={(e) => set({ announcement_link_text: e.target.value })} placeholder="Shop now" className={inputCls} />
              </Field>
              <Field label="Link goes to" error={errors.announcement_link_url}>
                <input maxLength={300} value={form.announcement_link_url} onChange={(e) => set({ announcement_link_url: e.target.value })} placeholder="/collections/diwali-edit" className={inputCls} />
              </Field>
            </div>
            <Toggle label="Show a countdown to the end" help="“Ends in 20d 04h 12m” in the announcement bar." checked={form.show_countdown} onChange={(on) => set({ show_countdown: on })} />
          </section>

          <section className={`${cardCls} space-y-4`} aria-label="Collection and sale">
            <h2 className="font-medium text-gray-900">Featured collection and sale</h2>
            <Field label="Collection" error={errors.collection_id} help="Make collections under Collections.">
              <select value={form.collection_id} onChange={(e) => set({ collection_id: e.target.value })} className={inputCls}>
                <option value="">None</option>
                {(collections.data?.collections || []).map((c) => <option key={c.id} value={c.id}>{c.name} ({c.product_count} products)</option>)}
              </select>
            </Field>
            <Field label="Sale discount on that collection (%)" error={errors.sale_percent} help="Optional. Taken off the selling price of every product in the collection while the campaign is live, then removed. Your product prices are not changed.">
              <input type="number" min="1" max="90" step="0.5" value={form.sale_percent} onChange={(e) => set({ sale_percent: e.target.value })} className={inputCls} />
            </Field>
          </section>

          <section className={`${cardCls} space-y-4`} aria-label="Festive look">
            <h2 className="font-medium text-gray-900">Festive look</h2>
            <Toggle
              label="Switch on festive decoration" checked={form.decoration_enabled} onChange={(on) => set({ decoration_enabled: on })}
              help="Small accents only — a scalloped border under the announcement bar, corner ornaments on the hero, and an accent colour for sale badges, the countdown and the hero button. Your store’s colours and fonts stay as they are."
            />
            <fieldset disabled={!form.decoration_enabled} className="disabled:opacity-50">
              <legend className="mb-2 text-xs font-medium text-gray-600">Accent colour</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {presets.map((p) => (
                  <label key={p.value} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${form.accent_preset === p.value ? 'border-gray-900' : 'border-gray-200'}`}>
                    <input type="radio" name="accent" value={p.value} checked={form.accent_preset === p.value} onChange={() => set({ accent_preset: p.value })} />
                    <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: p.accent, color: p.on_accent }}>Sale · 20% off</span>
                    <span className="text-sm text-gray-800">{p.label}</span>
                  </label>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-500">Each choice has been checked for readable contrast.</p>
            </fieldset>
          </section>
        </div>
      </form>

      {/* Outside the form above: this section has a small form of its own. */}
      <div className="mt-6">
        <Coupons campaign={data} chosen={coupons} setChosen={setCoupons} />
        <p className="mt-2 text-xs text-gray-500">Ticking or unticking a coupon takes effect when you press “{isNew ? 'Schedule campaign' : 'Save campaign'}”.</p>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        {isNew ? (
          <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-600 xl:col-span-2">
            Hero slides and promo banners can be added once the campaign has been scheduled.
          </p>
        ) : data && (
          <>
            <Attachments
              campaign={data} kind="banners" title="Hero slides" onChange={reload}
              hint="Shown in the home page slider instead of the usual slides while the campaign is live. With none, the usual slides stay."
            />
            <Attachments
              campaign={data} kind="promo-banners" title="Promo banners" onChange={reload}
              hint="Shown in the home page’s promo block instead of the usual one while the campaign is live."
            />
          </>
        )}
      </div>
    </div>
  )
}

export default function AdminCampaigns() {
  const { id } = useParams()
  return id ? <CampaignEditor key={id} id={id} /> : <CampaignList />
}
