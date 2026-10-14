/* An address written out the way it goes on a parcel. */
export default function AddressBlock({ address, className = '' }) {
  if (!address) return null
  return (
    <address className={`not-italic text-sm leading-relaxed text-muted ${className}`}>
      <span className="font-medium text-fg">{address.full_name}</span>
      <br />
      {address.line1}
      {address.line2 ? `, ${address.line2}` : ''}
      <br />
      {address.city}, {address.state} {address.pin_code}
      <br />
      <span className="tabular-nums">{address.phone}</span>
    </address>
  )
}
