import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconPackage, IconHeart, IconMapPin, IconUser, IconLogout, IconPlus, IconTrash, IconStarFilled } from '@tabler/icons-react'
import { useAuthStore } from '@/store/useAuthStore'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'

const inr = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : ''

const STATUS_STYLES = {
  pending: 'text-blue-600 bg-blue-50',
  confirmed: 'text-blue-600 bg-blue-50',
  packed: 'text-gold bg-cream',
  shipped: 'text-gold bg-cream',
  out_for_delivery: 'text-gold bg-cream',
  delivered: 'text-green-600 bg-green-50',
  cancelled: 'text-maroon-light bg-red-50',
  return_requested: 'text-orange-600 bg-orange-50',
  returned: 'text-gray bg-surface',
}

const emptyAddr = { full_name: '', phone: '', line1: '', line2: '', city: '', state: '', pin_code: '' }

export default function Dashboard() {
  const { user, setUser, logout } = useAuthStore()
  const navigate = useNavigate()
  const [tab, setTab] = useState('orders')

  const handleLogout = () => { logout(); navigate('/') }

  const initials = user?.full_name
    ? user.full_name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : '??'

  const NAV = [
    { key: 'orders', icon: IconPackage, label: 'My Orders' },
    { key: 'addresses', icon: IconMapPin, label: 'Addresses' },
    { key: 'profile', icon: IconUser, label: 'Profile' },
  ]

  return (
    <>
      {/* Sidebar */}
      <aside className="border-r border-line p-5 bg-white hidden lg:block">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-line">
          <div className="w-10 h-10 rounded-full bg-ink flex items-center justify-center text-gold font-bold text-sm">{initials}</div>
          <div>
            <div className="font-semibold text-sm">{user?.full_name || 'User'}</div>
            <div className="text-[11px] text-gray">{user?.email || ''}</div>
          </div>
        </div>
        <nav className="space-y-1">
          {NAV.map((n) => (
            <button
              key={n.key}
              onClick={() => setTab(n.key)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-xs rounded transition-colors ${tab === n.key ? 'bg-cream text-ink font-semibold' : 'text-gray hover:bg-surface'}`}
            >
              <n.icon size={16} /> {n.label}
            </button>
          ))}
          <button onClick={() => navigate('/wishlist')} className="w-full flex items-center gap-3 px-3 py-2.5 text-xs rounded text-gray hover:bg-surface transition-colors">
            <IconHeart size={16} /> Wishlist
          </button>
          <button onClick={handleLogout} className="w-full flex items-center gap-3 px-3 py-2.5 text-xs rounded text-maroon-light hover:bg-red-50 transition-colors">
            <IconLogout size={16} /> Logout
          </button>
        </nav>
      </aside>

      {/* Main */}
      <div className="p-6 lg:p-8">
        {/* Mobile tab switch */}
        <div className="flex gap-2 mb-6 lg:hidden overflow-x-auto">
          {NAV.map((n) => (
            <button key={n.key} onClick={() => setTab(n.key)} className={`px-4 py-2 text-xs whitespace-nowrap rounded-full border ${tab === n.key ? 'border-gold bg-gold text-white' : 'border-line text-gray'}`}>{n.label}</button>
          ))}
        </div>

        {tab === 'orders' && <OrdersTab />}
        {tab === 'addresses' && <AddressesTab />}
        {tab === 'profile' && <ProfileTab user={user} setUser={setUser} />}
      </div>
    </>
  )
}

// Statuses where a return may still be possible. The API is the authority —
// this only decides whether to offer the button, and /returns/eligibility
// decides which items inside the order actually qualify.
const RETURNABLE_STATUSES = ['delivered', 'return_requested']

function OrdersTab() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [returningOrder, setReturningOrder] = useState(null)

  const load = () => {
    apiClient.get('/orders')
      .then(({ data }) => setOrders(data.orders))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  return (
    <>
      <h1 className="font-serif text-2xl font-bold">My Orders</h1>
      <p className="text-xs text-gray mt-1">Track, return, or buy things again</p>

      {loading ? (
        <div className="py-16 text-center text-gray text-sm">Loading orders…</div>
      ) : orders.length === 0 ? (
        <div className="py-16 text-center">
          <IconPackage size={40} className="text-line mx-auto" />
          <p className="text-gray text-sm mt-4">You haven't placed any orders yet</p>
          <Link to="/shop" className="inline-block mt-4 px-6 py-2.5 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors">Start Shopping</Link>
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {orders.map((o) => (
            <div key={o.id} className="border border-line p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <div className="font-medium text-sm">{o.order_number}</div>
                <div className="text-[11px] text-gray mt-0.5">{fmtDate(o.placed_at)} · {o.item_count} item{o.item_count !== 1 ? 's' : ''}</div>
                {o.item_summary && <div className="text-[11px] text-gray mt-0.5">{o.item_summary}</div>}
              </div>
              <div className="flex items-center gap-4">
                <span className={`px-2.5 py-1 text-[10px] tracking-[1px] uppercase font-bold capitalize ${STATUS_STYLES[o.status] || 'text-gray bg-surface'}`}>{o.status.replace(/_/g, ' ')}</span>
                <span className="font-semibold text-sm">{inr(o.total_amount)}</span>
                <Link to={`/track-order?order=${o.order_number}`} className="text-[11px] text-gold font-medium hover:underline">Track</Link>
                {RETURNABLE_STATUSES.includes(o.status) && (
                  <button
                    onClick={() => setReturningOrder(o)}
                    className="text-[11px] text-gold font-medium hover:underline"
                  >
                    Return
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {returningOrder && (
        <ReturnModal
          order={returningOrder}
          onClose={() => setReturningOrder(null)}
          onSubmitted={() => { setReturningOrder(null); load() }}
        />
      )}
    </>
  )
}

const RETURN_REASONS = [
  { value: 'size_issue', label: 'Size or fit issue' },
  { value: 'wrong_item', label: 'Wrong item delivered' },
  { value: 'damaged', label: 'Arrived damaged' },
  { value: 'quality_issue', label: 'Quality not as expected' },
  { value: 'not_as_described', label: 'Not as described' },
  { value: 'changed_mind', label: 'Changed my mind' },
  { value: 'other', label: 'Other' },
]

function ReturnModal({ order, onClose, onSubmitted }) {
  const [eligibility, setEligibility] = useState(null)
  const [itemId, setItemId] = useState(null)
  const [reason, setReason] = useState('size_issue')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiClient.get(`/returns/eligibility/${order.id}`)
      .then(({ data }) => {
        setEligibility(data)
        const first = data.items.find((i) => i.returnable)
        if (first) setItemId(first.order_item_id)
      })
      .catch(() => setError('Could not load return options. Please try again.'))
  }, [order.id])

  const submit = async () => {
    if (!itemId) return
    setSubmitting(true)
    setError('')
    try {
      await apiClient.post('/returns', {
        order_item_id: itemId,
        reason,
        description: description || undefined,
      })
      onSubmitted()
    } catch (err) {
      setError(err?.response?.data?.error || 'Could not submit the return request.')
    } finally {
      setSubmitting(false)
    }
  }

  const anyReturnable = eligibility?.items?.some((i) => i.returnable)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md max-h-[85vh] overflow-y-auto bg-white p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-xl font-bold">Request a Return</h2>
        <p className="text-[11px] text-gray mt-1">
          Order {order.order_number}
          {eligibility && ` · within ${eligibility.window_days} days of delivery`}
        </p>

        {!eligibility && !error && (
          <div className="py-10 text-center text-gray text-sm">Loading…</div>
        )}

        {eligibility && !anyReturnable && (
          <p className="mt-5 text-sm text-gray">
            No items in this order can be returned right now.
            {!eligibility.window_open && ' The return window has closed.'}
          </p>
        )}

        {eligibility && anyReturnable && (
          <div className="mt-5 space-y-4">
            <div>
              <label className="text-[11px] tracking-[1px] uppercase font-bold text-gray">Item</label>
              <div className="mt-2 space-y-2">
                {eligibility.items.map((i) => (
                  <label
                    key={i.order_item_id}
                    className={`flex items-start gap-2 border p-3 text-sm ${
                      i.returnable ? 'border-line cursor-pointer' : 'border-line/50 opacity-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="return-item"
                      className="mt-1"
                      disabled={!i.returnable}
                      checked={itemId === i.order_item_id}
                      onChange={() => setItemId(i.order_item_id)}
                    />
                    <span>
                      <span className="block">{i.product_name}</span>
                      <span className="block text-[11px] text-gray">
                        {[i.size, i.color_name].filter(Boolean).join(' · ')} · Qty {i.quantity}
                      </span>
                      {i.reason_unavailable && (
                        <span className="block text-[11px] text-gray italic mt-0.5">{i.reason_unavailable}</span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[11px] tracking-[1px] uppercase font-bold text-gray">Reason</label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-2 w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-gold"
              >
                {RETURN_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>

            <div>
              <label className="text-[11px] tracking-[1px] uppercase font-bold text-gray">
                Anything else? (optional)
              </label>
              <textarea
                rows={3}
                value={description}
                maxLength={2000}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-2 w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-gold"
              />
            </div>
          </div>
        )}

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-line py-2.5 text-[11px] tracking-[2px] uppercase font-bold hover:bg-surface transition-colors"
          >
            Cancel
          </button>
          {anyReturnable && (
            <button
              onClick={submit}
              disabled={submitting || !itemId}
              className="flex-1 bg-ink text-white py-2.5 text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-50"
            >
              {submitting ? 'Submitting…' : 'Submit'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function AddressesTab() {
  const [addresses, setAddresses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyAddr)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    apiClient.get('/addresses').then(({ data }) => setAddresses(data.addresses)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const save = async (e) => {
    e.preventDefault()
    if (form.pin_code.length !== 6) return toast.error('Pincode must be 6 digits')
    setSaving(true)
    try {
      await apiClient.post('/addresses', { ...form, is_default: addresses.length === 0 })
      toast.success('Address added')
      setForm(emptyAddr); setShowForm(false); load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not save address')
    }
    setSaving(false)
  }

  const del = async (id) => {
    if (!confirm('Delete this address?')) return
    await apiClient.delete(`/addresses/${id}`)
    load()
  }

  const setDefault = async (id) => {
    await apiClient.patch(`/addresses/${id}/default`)
    load()
  }

  const inputCls = 'w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-gold transition-colors'

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-serif text-2xl font-bold">My Addresses</h1>
          <p className="text-xs text-gray mt-1">Manage your delivery addresses</p>
        </div>
        {!showForm && <button onClick={() => setShowForm(true)} className="flex items-center gap-1.5 px-4 py-2.5 bg-ink text-white text-[11px] tracking-[1px] uppercase font-bold hover:bg-ink/90 transition-colors"><IconPlus size={14} /> Add</button>}
      </div>

      {showForm && (
        <form onSubmit={save} className="mt-5 border border-line p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input required placeholder="Full Name *" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} className={inputCls} />
          <input required placeholder="Phone *" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} className={inputCls} />
          <input required placeholder="Address line *" value={form.line1} onChange={(e) => setForm((f) => ({ ...f, line1: e.target.value }))} className={`${inputCls} md:col-span-2`} />
          <input placeholder="Landmark / Apartment" value={form.line2} onChange={(e) => setForm((f) => ({ ...f, line2: e.target.value }))} className={`${inputCls} md:col-span-2`} />
          <input required placeholder="City *" value={form.city} onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))} className={inputCls} />
          <input required placeholder="State *" value={form.state} onChange={(e) => setForm((f) => ({ ...f, state: e.target.value }))} className={inputCls} />
          <input required placeholder="Pincode *" value={form.pin_code} onChange={(e) => setForm((f) => ({ ...f, pin_code: e.target.value.replace(/\D/g, '').slice(0, 6) }))} className={inputCls} />
          <div className="md:col-span-2 flex gap-2">
            <button type="submit" disabled={saving} className="px-6 py-2.5 bg-gold text-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-gold-light transition-colors disabled:opacity-60">{saving ? 'Saving…' : 'Save'}</button>
            <button type="button" onClick={() => { setShowForm(false); setForm(emptyAddr) }} className="px-6 py-2.5 border border-line text-[11px] tracking-[2px] uppercase font-bold hover:border-ink transition-colors">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="py-16 text-center text-gray text-sm">Loading…</div>
      ) : addresses.length === 0 && !showForm ? (
        <div className="py-16 text-center text-gray text-sm">No addresses saved yet</div>
      ) : (
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          {addresses.map((a) => (
            <div key={a.id} className="border border-line p-4">
              <div className="flex items-start justify-between">
                <div className="text-sm">
                  <div className="font-medium">{a.full_name} <span className="text-gray font-normal">· {a.phone}</span></div>
                  <div className="text-xs text-gray mt-1">{a.line1}{a.line2 ? `, ${a.line2}` : ''}, {a.city}, {a.state} - {a.pin_code}</div>
                  {a.is_default && <span className="inline-block mt-2 text-[9px] tracking-[1px] uppercase text-gold font-bold">Default</span>}
                </div>
                <button onClick={() => del(a.id)} className="text-gray hover:text-maroon-light"><IconTrash size={16} /></button>
              </div>
              {!a.is_default && <button onClick={() => setDefault(a.id)} className="mt-3 text-[11px] text-gold font-medium hover:underline flex items-center gap-1"><IconStarFilled size={11} /> Set as default</button>}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function ProfileTab({ user, setUser }) {
  const [form, setForm] = useState({ full_name: user?.full_name || '', phone: user?.phone || '' })
  const [saving, setSaving] = useState(false)
  const [pwd, setPwd] = useState({ current_password: '', new_password: '' })
  const [changingPwd, setChangingPwd] = useState(false)

  const saveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const { data } = await apiClient.put('/profile', form)
      setUser(data)
      toast.success('Profile updated')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Update failed')
    }
    setSaving(false)
  }

  const changePassword = async (e) => {
    e.preventDefault()
    if (pwd.new_password.length < 8) return toast.error('New password must be at least 8 characters')
    setChangingPwd(true)
    try {
      await apiClient.put('/profile/password', pwd)
      toast.success('Password updated')
      setPwd({ current_password: '', new_password: '' })
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not change password')
    }
    setChangingPwd(false)
  }

  const inputCls = 'w-full border border-line px-4 py-3 text-sm outline-none focus:border-gold transition-colors'
  const labelCls = 'text-[11px] font-semibold uppercase tracking-[0.5px] text-gray block mb-1.5'

  return (
    <>
      <h1 className="font-serif text-2xl font-bold">Profile</h1>
      <p className="text-xs text-gray mt-1">Manage your personal information</p>

      <form onSubmit={saveProfile} className="mt-6 max-w-md space-y-4">
        <div><label className={labelCls}>Full Name</label><input value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} className={inputCls} /></div>
        <div><label className={labelCls}>Phone</label><input value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} className={inputCls} /></div>
        <div><label className={labelCls}>Email</label><input value={user?.email || ''} disabled className={`${inputCls} bg-surface text-gray`} /></div>
        <button type="submit" disabled={saving} className="px-6 py-3 bg-ink text-white text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink/90 transition-colors disabled:opacity-60">{saving ? 'Saving…' : 'Save Changes'}</button>
      </form>

      <form onSubmit={changePassword} className="mt-10 max-w-md space-y-4 border-t border-line pt-8">
        <h2 className="font-serif text-lg font-bold">Change Password</h2>
        <div><label className={labelCls}>Current Password</label><input type="password" value={pwd.current_password} onChange={(e) => setPwd((p) => ({ ...p, current_password: e.target.value }))} className={inputCls} required /></div>
        <div><label className={labelCls}>New Password</label><input type="password" value={pwd.new_password} onChange={(e) => setPwd((p) => ({ ...p, new_password: e.target.value }))} className={inputCls} required /></div>
        <button type="submit" disabled={changingPwd} className="px-6 py-3 border border-ink text-[11px] tracking-[2px] uppercase font-bold hover:bg-ink hover:text-white transition-colors disabled:opacity-60">{changingPwd ? 'Updating…' : 'Update Password'}</button>
      </form>
    </>
  )
}
