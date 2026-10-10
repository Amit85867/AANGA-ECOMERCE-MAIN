import { useCallback, useEffect, useState } from 'react'
import { IconMapPin, IconPlus } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { toast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { Modal } from '@/components/ui/Overlay'
import AddressForm from '@/components/account/AddressForm'
import AddressBlock from '@/components/account/AddressBlock'
import { Badge, EmptyState, ErrorState, Skeleton } from '@/components/ui/Display'
import Seo from '@/components/Seo'

export default function Addresses() {
  const [addresses, setAddresses] = useState(null)
  const [failed, setFailed] = useState(false)
  const [editing, setEditing] = useState(null)     // null | 'new' | address
  const [deleting, setDeleting] = useState(null)   // address pending confirmation
  const [working, setWorking] = useState(false)

  const load = useCallback(() => {
    setFailed(false)
    return apiClient.get('/addresses')
      .then(({ data }) => setAddresses(data.addresses))
      .catch(() => setFailed(true))
  }, [])

  useEffect(() => { load() }, [load])

  const makeDefault = async (address) => {
    try {
      await apiClient.patch(`/addresses/${address.id}/default`)
      toast.success('Default address updated')
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not update the default address')
    }
  }

  const remove = async () => {
    setWorking(true)
    try {
      await apiClient.delete(`/addresses/${deleting.id}`)
      toast.success('Address removed')
      setDeleting(null)
      load()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not remove the address')
    }
    setWorking(false)
  }

  return (
    <>
      <Seo title="My Addresses" noindex />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-3xl text-fg">Addresses</h1>
          <p className="mt-2 text-sm text-muted">Where we deliver your orders.</p>
        </div>
        {addresses?.length > 0 && (
          <Button onClick={() => setEditing('new')}><IconPlus size={16} /> Add address</Button>
        )}
      </div>

      <div className="mt-8">
        {failed ? (
          <ErrorState message="We could not load your addresses." onRetry={load} />
        ) : addresses === null ? (
          <div className="grid gap-4 sm:grid-cols-2"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
        ) : addresses.length === 0 ? (
          <EmptyState
            icon={IconMapPin} title="No saved addresses"
            hint="Add an address now and checkout will be quicker."
            action={<Button onClick={() => setEditing('new')}>Add address</Button>}
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {addresses.map((a) => (
              <li key={a.id}>
                <Card className="flex h-full flex-col p-5">
                  <div className="flex items-start justify-between gap-3">
                    <AddressBlock address={a} />
                    {a.is_default && <Badge tone="dark">Default</Badge>}
                  </div>
                  <div className="mt-auto flex flex-wrap gap-x-5 gap-y-2 pt-5 text-sm">
                    <button type="button" onClick={() => setEditing(a)} className="font-medium text-fg underline underline-offset-2">Edit</button>
                    {!a.is_default && (
                      <button type="button" onClick={() => makeDefault(a)} className="font-medium text-fg underline underline-offset-2">Make default</button>
                    )}
                    <button type="button" onClick={() => setDeleting(a)} className="font-medium text-danger underline underline-offset-2">Remove</button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Modal
        open={Boolean(editing)} onClose={() => setEditing(null)} size="lg"
        title={editing === 'new' ? 'Add address' : 'Edit address'}
      >
        {editing && (
          <AddressForm
            // Remount per address so the form never shows the previous one's values.
            key={editing === 'new' ? 'new' : editing.id}
            address={editing === 'new' ? null : editing}
            forceDefault={addresses?.length === 0}
            onCancel={() => setEditing(null)}
            onSaved={() => { setEditing(null); load() }}
          />
        )}
      </Modal>

      <Modal
        open={Boolean(deleting)} onClose={() => setDeleting(null)} title="Remove this address?" size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleting(null)} disabled={working} data-autofocus>Keep it</Button>
            <Button variant="danger" onClick={remove} disabled={working}>{working ? 'Removing…' : 'Remove'}</Button>
          </>
        }
      >
        {deleting && (
          <>
            <AddressBlock address={deleting} />
            <p className="mt-4 text-sm text-muted">
              Orders already sent to this address keep it on record. It is only removed from your address book.
            </p>
          </>
        )}
      </Modal>
    </>
  )
}
