import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '@/services/apiClient'
import { useCampaign, useCampaignEpoch } from '@/store/useLayoutStore'
import { Countdown, FestiveBorder } from '@/components/layout/Festive'

export default function AnnounceBar() {
  const [announcement, setAnnouncement] = useState(null)
  const [loaded, setLoaded] = useState(false)
  const campaign = useCampaign()
  const epoch = useCampaignEpoch()

  // Asked again whenever a campaign starts or ends: its line replaces the
  // everyday announcement for exactly as long as it is live.
  useEffect(() => {
    apiClient.get('/cms/announcements')
      .then((r) => setAnnouncement(r.data.announcements?.[0] || null))
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [epoch])

  const countdown = campaign?.show_countdown ? campaign.ends_at : null

  // Loading: an empty bar of the final height (same as the shell in
  // index.html). Loaded with nothing to announce: no bar at all.
  if (!loaded) return <div className="h-9 bg-black" aria-hidden="true" />
  if (!announcement && !countdown) return null

  const a = announcement || { bg_color: '#0A0A0A', text_color: '#ffffff' }

  return (
    // Colours stay CMS-controlled (admin sets them); only the type scale is
    // aligned to the design system here.
    <div
      className="relative flex min-h-9 flex-wrap items-center justify-center gap-x-1 gap-y-1 px-4 py-2 text-center text-xs font-medium tracking-[0.1em] uppercase"
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
      {countdown && <Countdown endsAt={countdown} className="ml-2" />}
      <FestiveBorder />
    </div>
  )
}
