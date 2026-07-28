import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'

export default function AnnounceBar() {
  const [announcement, setAnnouncement] = useState(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    apiClient.get('/cms/announcements')
      .then((r) => {
        if (r.data.announcements?.length) setAnnouncement(r.data.announcements[0])
      })
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [])

  if (!loaded || !announcement) return null

  const a = announcement

  return (
    // Colours stay CMS-controlled (admin sets them); only the type scale is
    // aligned to the design system here.
    <div
      className="text-center py-2.5 px-4 text-[11px] font-medium tracking-[0.1em] uppercase"
      style={{ backgroundColor: a.bg_color, color: a.text_color }}
    >
      {a.text}{' '}
      {a.highlight_text && (
        <span className="font-semibold" style={{ color: a.highlight_color }}>
          {a.highlight_text}
        </span>
      )}
      {a.link_text && a.link_url && (
        <Link to={a.link_url} className="ml-2 underline underline-offset-2 hover:opacity-80">
          {a.link_text}
        </Link>
      )}
    </div>
  )
}
