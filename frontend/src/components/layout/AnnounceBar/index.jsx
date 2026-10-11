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
      // One line of fixed height on a phone (the same 36px the page shell
      // reserves), so the page below never moves when this arrives. Wider
      // screens have room for the whole message.
      className="relative flex h-9 items-center justify-center gap-x-1 px-3 text-center text-xs font-medium tracking-[0.1em] uppercase sm:h-auto sm:min-h-9 sm:flex-wrap sm:px-4 sm:py-2"
      style={{ backgroundColor: a.bg_color, color: a.text_color }}
    >
      {/* On a phone the offer and the countdown are what matter; the greeting
          joins them when there is room. */}
      <span className={a.highlight_text ? 'hidden sm:inline' : 'truncate'}>{a.text}</span>{' '}
      {a.highlight_text && (
        <span className="min-w-0 truncate font-semibold" style={{ color: a.highlight_color }}>
          {a.highlight_text}
        </span>
      )}
      {a.link_text && a.link_url && (
        <Link to={a.link_url} className="ml-2 hidden shrink-0 underline underline-offset-2 hover:opacity-80 sm:inline">
          {a.link_text}
        </Link>
      )}
      {countdown && <Countdown endsAt={countdown} className="ml-2 shrink-0" />}
      <FestiveBorder />
    </div>
  )
}
