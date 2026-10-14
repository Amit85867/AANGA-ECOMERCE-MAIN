/* The eyebrow + title that opens every home page section. */
export default function SectionHeading({ id, eyebrow, title, children, center = false, invert = false }) {
  return (
    <div className={`mb-8 flex flex-wrap items-end justify-between gap-4 lg:mb-10 ${center ? 'justify-center text-center' : ''}`}>
      <div>
        {eyebrow && (
          <p className={`text-xs font-semibold uppercase tracking-[0.15em] ${invert ? 'text-white/70' : 'text-muted'}`}>
            {eyebrow}
          </p>
        )}
        <h2 id={id} className={`display mt-2 text-3xl sm:text-4xl ${invert ? 'text-white' : 'text-fg'}`}>{title}</h2>
      </div>
      {children}
    </div>
  )
}
