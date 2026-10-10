import { useCallback, useState } from 'react'
import { IconBrandGoogle } from '@tabler/icons-react'
import { toast } from '@/components/ui/toastStore'
import Button from '@/components/ui/Button'
import { useAuthStore } from '@/store/useAuthStore'
import { useFeatures } from '@/store/useFeaturesStore'

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

function loadGoogleScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts) return resolve()
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

/*
 * "Continue with Google", plus the "or" divider beneath it.
 *
 * Renders nothing unless both halves are configured: the server has a client
 * id to verify tokens against, and this build was given the same id. A button
 * that can only fail is worse than no button.
 */
export default function GoogleButton({ onSignedIn }) {
  const googleAuth = useAuthStore((s) => s.googleAuth)
  const { google_login: enabled } = useFeatures()
  const [working, setWorking] = useState(false)

  const signIn = useCallback(async () => {
    setWorking(true)
    try {
      await loadGoogleScript()
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: 'email profile',
        callback: async (response) => {
          if (!response.access_token) return setWorking(false)
          try {
            await googleAuth(response.access_token)
            onSignedIn()
          } catch {
            toast.error('Google sign-in did not complete. Please try again.')
          }
          setWorking(false)
        },
        error_callback: () => setWorking(false),   // window closed without choosing
      })
      client.requestAccessToken()
    } catch {
      toast.error('Could not reach Google. Check your connection and try again.')
      setWorking(false)
    }
  }, [googleAuth, onSignedIn])

  if (!enabled || !CLIENT_ID) return null

  return (
    <>
      <Button variant="secondary" full onClick={signIn} disabled={working}>
        <IconBrandGoogle size={18} aria-hidden="true" />
        {working ? 'Waiting for Google…' : 'Continue with Google'}
      </Button>
      <div className="my-6 flex items-center gap-3" aria-hidden="true">
        <div className="h-px flex-1 bg-hairline/60" />
        <span className="text-xs uppercase tracking-[0.1em] text-subtle">or</span>
        <div className="h-px flex-1 bg-hairline/60" />
      </div>
    </>
  )
}
