import { useState } from 'react'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Chip from '@/components/ui/Chip'
import Card from '@/components/ui/Card'

/*
 * Living reference for the "Premium Editorial Commerce" design system.
 * Internal only (route: /style-guide) — not linked from the storefront.
 * Keep this in sync as primitives are added; it is how we review the system
 * while migrating screens phase by phase.
 */

const SWATCHES = [
  ['bg', 'Canvas', 'bg-bg'],
  ['card', 'Card', 'bg-card'],
  ['fill', 'Fill', 'bg-fill'],
  ['fill-strong', 'Fill strong', 'bg-fill-strong'],
  ['fg', 'Text', 'bg-fg'],
  ['muted', 'Muted', 'bg-muted'],
  ['subtle', 'Subtle', 'bg-subtle'],
  ['hairline', 'Hairline', 'bg-hairline'],
  ['primary', 'Primary', 'bg-primary'],
  ['accent', 'Accent', 'bg-accent'],
  ['accent-soft', 'Accent soft', 'bg-accent-soft'],
  ['danger', 'Danger', 'bg-danger'],
]

function Section({ title, children }) {
  return (
    <section className="mb-16">
      <h2 className="display text-2xl mb-6 text-fg">{title}</h2>
      {children}
    </section>
  )
}

export default function StyleGuide() {
  const [size, setSize] = useState('M')
  const [color, setColor] = useState('#191c1e')

  return (
    <div className="min-h-screen bg-bg">
      {/* Glassmorphic nav — the pattern used by the real navbar in UI Phase 2 */}
      <header className="glass sticky top-0 z-10 border-b border-hairline">
        <div className="max-w-[1280px] mx-auto px-12 h-16 flex items-center justify-between">
          <span className="display text-xl">AANGA</span>
          <span className="text-xs uppercase tracking-[0.05em] text-muted">Design System</span>
        </div>
      </header>

      <main className="max-w-[1280px] mx-auto px-12 py-16">
        <h1 className="display text-5xl mb-2 text-fg">Premium Editorial Commerce</h1>
        <p className="text-lg text-muted mb-16">
          Monochrome editorial canvas with a single pink accent, on an 8px grid.
        </p>

        <Section title="Colour">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {SWATCHES.map(([token, label, cls]) => (
              <div key={token}>
                <div className={`${cls} h-20 rounded-card border border-hairline`} />
                <div className="mt-2 text-sm font-medium text-fg">{label}</div>
                <div className="text-xs text-subtle font-mono">--color-{token}</div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Typography">
          <div className="space-y-4">
            <p className="display text-5xl text-fg">Display — Poppins 48/700</p>
            <p className="display text-3xl text-fg">Headline — Poppins 32/600</p>
            <p className="text-lg text-muted">Body large — Inter 18/400</p>
            <p className="text-base text-muted">Body medium — Inter 16/400</p>
            <p className="text-sm font-semibold tracking-[0.05em] uppercase text-fg">
              Button — Inter 14/600
            </p>
            <p className="text-xs font-medium text-subtle">Label small — Inter 12/500</p>
          </div>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap items-center gap-4 mb-6">
            <Button variant="primary">Add to Bag</Button>
            <Button variant="secondary">Wishlist</Button>
            <Button variant="subtle">Subtle</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="accent">Sale</Button>
            <Button disabled>Disabled</Button>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Button size="sm">Small</Button>
            <Button size="md">Medium</Button>
            <Button size="lg">Large</Button>
            <Button pill>Pill</Button>
          </div>
        </Section>

        <Section title="Inputs">
          <div className="grid md:grid-cols-3 gap-6 max-w-3xl">
            <Input label="Email" name="sg-email" placeholder="you@example.com" />
            <Input label="Search" name="sg-search" placeholder="Search collections…" pill />
            <Input label="Postal code" name="sg-pin" defaultValue="70001" error="Must be 6 digits" />
          </div>
        </Section>

        <Section title="Chips">
          <div className="mb-6">
            <div className="text-xs uppercase tracking-[0.05em] text-muted mb-3">Select size</div>
            <div className="flex gap-3">
              {['S', 'M', 'L', 'XL'].map((s) => (
                <Chip key={s} selected={size === s} onClick={() => setSize(s)}>{s}</Chip>
              ))}
              <Chip disabled>XXL</Chip>
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.05em] text-muted mb-3">Colour</div>
            <div className="flex gap-3">
              {['#191c1e', '#f8f9fb', '#44544f', '#f53765'].map((c) => (
                <Chip key={c} color={c} selected={color === c} onClick={() => setColor(c)} aria-label={c} />
              ))}
            </div>
          </div>
        </Section>

        <Section title="Elevation">
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="p-6">
              <div className="font-semibold text-fg">Card</div>
              <div className="text-sm text-muted mt-1">rounded-card · shadow-card</div>
            </Card>
            <Card hover className="p-6">
              <div className="font-semibold text-fg">Card — hover lift</div>
              <div className="text-sm text-muted mt-1">hover:shadow-lift</div>
            </Card>
            <Card block className="p-6">
              <div className="font-semibold text-fg">Block</div>
              <div className="text-sm text-muted mt-1">rounded-block (24px)</div>
            </Card>
          </div>
        </Section>
      </main>
    </div>
  )
}
