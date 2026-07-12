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
    <div
      className="text-center py-2 px-4 text-[11px] tracking-[1.5px] uppercase"
      style={{ backgroundColor: a.bg_color, color: a.text_color + 'd9' }}
    >
      {a.text}{' '}
      {a.highlight_text && <span style={{ color: a.highlight_color }}>{a.highlight_text}</span>}
      {a.link_text && a.link_url && (
        <Link to={a.link_url} className="ml-2 underline hover:opacity-80">{a.link_text}</Link>
      )}
    </div>
  )
}
