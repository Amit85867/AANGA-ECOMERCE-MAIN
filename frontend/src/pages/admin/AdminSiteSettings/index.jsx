import { useEffect, useState } from 'react'
import adminApi from '@/services/adminApi'
import { notifyError } from '@/components/admin/helpers'
import { IconDeviceFloppy } from '@tabler/icons-react'

const GROUP_LABELS = {
  general: 'General',
  content: 'Homepage Text (headings, newsletter, footer)',
  contact: 'Contact Information',
  tax: 'Tax Settings',
  shipping: 'Shipping Settings',
  social: 'Social Media Links',
  stats: 'Homepage Statistics',
}

const GROUP_ORDER = ['general', 'content', 'contact', 'tax', 'shipping', 'social', 'stats']

export default function AdminSiteSettings() {
  const [settings, setSettings] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [values, setValues] = useState({})

  const fetchSettings = () => {
    setLoading(true)
    adminApi.get('/admin/site-settings')
      .then((r) => {
        setSettings(r.data.settings)
        const vals = {}
        for (const s of r.data.settings) vals[s.key] = s.value
        setValues(vals)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchSettings() }, [])

  const handleSave = async () => {
    setSaving(true)
    const payload = settings.map((s) => ({
      key: s.key,
      value: values[s.key] ?? s.value,
      label: s.label,
      group_name: s.group_name,
    }))
    try {
      await adminApi.put('/admin/site-settings', { settings: payload })
      fetchSettings()
    } catch (err) {
      notifyError(err, 'Save failed')
    }
    setSaving(false)
  }

  const grouped = {}
  for (const s of settings) {
    const g = s.group_name || 'general'
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(s)
  }

  const inputCls = 'w-full rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-[#C8963E]'

  if (loading) return <div className="py-20 text-center text-gray-400">Loading...</div>

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Site Settings</h1>
          <p className="mt-1 text-sm text-gray-500">Configure store-wide settings, shipping, tax, and social links</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-[#C8963E] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#b88534] disabled:opacity-50">
          <IconDeviceFloppy size={18} /> {saving ? 'Saving...' : 'Save All'}
        </button>
      </div>

      <div className="space-y-6">
        {GROUP_ORDER.filter((g) => grouped[g]).map((group) => (
          <div key={group} className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-lg font-medium text-gray-900">{GROUP_LABELS[group] || group}</h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {grouped[group].map((s) => (
                <div key={s.key}>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{s.label || s.key}</label>
                  <input
                    value={values[s.key] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [s.key]: e.target.value }))}
                    className={inputCls}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Handle any ungrouped settings */}
        {Object.keys(grouped).filter((g) => !GROUP_ORDER.includes(g)).map((group) => (
          <div key={group} className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-lg font-medium text-gray-900 capitalize">{group}</h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {grouped[group].map((s) => (
                <div key={s.key}>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{s.label || s.key}</label>
                  <input
                    value={values[s.key] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [s.key]: e.target.value }))}
                    className={inputCls}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
