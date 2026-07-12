import { useEffect, useState } from 'react'
import { IconShieldCheck } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { useSetting } from '@/store/useSettingsStore'
import { FEATURE_ICONS } from '@/pages/admin/AdminFeatures'

export default function WhyChoose() {
  const [features, setFeatures] = useState([])
  const [loaded, setLoaded] = useState(false)
  const s = useSetting()

  useEffect(() => {
    apiClient.get('/cms/features')
      .then(({ data }) => setFeatures(data.features || []))
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [])

  if (!loaded || features.length === 0) return null

  return (
    <div className="bg-surface px-8 lg:px-12 py-14">
      <div className="text-center mb-10">
        <div className="text-[10px] tracking-[3px] text-gold uppercase font-semibold mb-2">{s('why_choose_tag', 'Our Promise')}</div>
        <h2 className="font-serif text-[34px] font-bold">{s('why_choose_title', 'Why Choose AANGA')}</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((f) => {
          const Icon = FEATURE_ICONS[f.icon] || IconShieldCheck
          return (
            <div key={f.id} className="bg-white p-7 border border-line hover:border-gold transition-colors">
              <div className="w-12 h-12 bg-ink flex items-center justify-center mb-4 overflow-hidden">
                {f.image_url ? (
                  <img src={f.image_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <Icon size={20} className="text-gold" />
                )}
              </div>
              <div className="font-serif text-base font-bold mb-2">{f.title}</div>
              {f.description && <p className="text-xs text-gray leading-[1.7]">{f.description}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
