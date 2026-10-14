import { useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useCampaignEpoch } from '@/store/useLayoutStore'
import { IconAdjustmentsHorizontal, IconSearchOff, IconX } from '@tabler/icons-react'
import apiClient from '@/services/apiClient'
import { useProductStore } from '@/store/useProductStore'
import ProductCard from '@/components/ui/ProductCard'
import Button from '@/components/ui/Button'
import Chip from '@/components/ui/Chip'
import { Select } from '@/components/ui/Field'
import { Drawer } from '@/components/ui/Overlay'
import {
  Container, EmptyState, ErrorState, PageTitle, ProductCardSkeleton,
} from '@/components/ui/Display'
import { inr } from '@/utils/format'
import Seo from '@/components/Seo'

const SORTS = [
  ['newest', 'Newest first'],
  ['price_asc', 'Price: low to high'],
  ['price_desc', 'Price: high to low'],
]
const PER_PAGE = 12

const list = (value) => (value ? value.split(',').filter(Boolean) : [])
const toggle = (items, item) => (items.includes(item) ? items.filter((i) => i !== item) : [...items, item])

function FilterGroup({ title, children }) {
  return (
    <fieldset className="border-b border-hairline/60 py-5 first:pt-0 last:border-0">
      <legend className="float-left w-full mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-fg">{title}</legend>
      <div className="clear-both">{children}</div>
    </fieldset>
  )
}

function Filters({ filters, facets, categories, set }) {
  const ceiling = Math.ceil((facets.price.max || 0) / 100) * 100
  const price = filters.maxPrice || ceiling

  return (
    <div>
      <FilterGroup title="Category">
        <div className="space-y-2.5">
          {[{ slug: '', name: 'All products' }, ...categories].map((c) => (
            <label key={c.slug || 'all'} className="flex items-center gap-2.5 text-sm text-fg cursor-pointer">
              <input
                type="radio" name="category" className="h-4 w-4 accent-black"
                checked={filters.category === c.slug}
                onChange={() => set({ category: c.slug })}
              />
              {c.name}
            </label>
          ))}
        </div>
      </FilterGroup>

      {facets.sizes.length > 0 && (
        <FilterGroup title="Size">
          <div className="flex flex-wrap gap-2">
            {facets.sizes.map((size) => (
              <Chip
                key={size} selected={filters.sizes.includes(size)} className="!h-10 !min-w-[2.75rem] !px-3"
                onClick={() => set({ sizes: toggle(filters.sizes, size) })}
              >
                {size}
              </Chip>
            ))}
          </div>
        </FilterGroup>
      )}

      {facets.colors.length > 0 && (
        <FilterGroup title="Colour">
          <div className="flex flex-wrap gap-3">
            {facets.colors.map((c) => (
              <Chip
                key={c.name} color={c.hex} selected={filters.colors.includes(c.name)}
                aria-label={c.name} title={c.name}
                onClick={() => set({ colors: toggle(filters.colors, c.name) })}
              />
            ))}
          </div>
        </FilterGroup>
      )}

      {ceiling > 0 && (
        <FilterGroup title="Price">
          <label htmlFor="max-price" className="sr-only">Maximum price</label>
          <input
            id="max-price" type="range" min={Math.floor(facets.price.min / 100) * 100} max={ceiling} step="100"
            value={price}
            onChange={(e) => set({ maxPrice: Number(e.target.value) >= ceiling ? 0 : Number(e.target.value) })}
            className="w-full accent-black"
          />
          <div className="mt-2 flex justify-between text-xs text-muted tabular-nums">
            <span>{inr(facets.price.min)}</span>
            <span className="font-medium text-fg">{filters.maxPrice ? `Up to ${inr(price)}` : 'Any price'}</span>
          </div>
        </FilterGroup>
      )}
    </div>
  )
}

export default function Shop() {
  const [params, setParams] = useSearchParams()
  // /collections/<slug> is this same page, narrowed to one hand-picked collection.
  const { slug: collectionSlug } = useParams()
  const [collection, setCollection] = useState(null)
  const epoch = useCampaignEpoch()
  const {
    products, loading, loadingMore, error, total, page, pages,
    fetchProducts, categories, fetchCategories,
  } = useProductStore()
  const [facets, setFacets] = useState({ sizes: [], colors: [], price: { min: 0, max: 0 } })
  const [drawerOpen, setDrawerOpen] = useState(false)

  // The URL is the single source of truth for filters: a filtered view can be
  // shared, bookmarked, and survives Back from a product page.
  const filters = useMemo(() => ({
    q: params.get('q') || '',
    category: params.get('category') || '',
    sizes: list(params.get('size')),
    colors: list(params.get('color')),
    maxPrice: Number(params.get('max_price')) || 0,
    sort: params.get('sort') || 'newest',
  }), [params])

  const set = (patch) => {
    const next = { ...filters, ...patch }
    const out = {}
    if (next.q) out.q = next.q
    if (next.category) out.category = next.category
    if (next.sizes.length) out.size = next.sizes.join(',')
    if (next.colors.length) out.color = next.colors.join(',')
    if (next.maxPrice) out.max_price = String(next.maxPrice)
    if (next.sort !== 'newest') out.sort = next.sort
    // Replace, so each filter click is not its own Back-button step.
    setParams(out, { replace: true })
  }

  const query = useMemo(() => {
    const out = { per_page: PER_PAGE, sort: filters.sort }
    if (collectionSlug) {
      out.collection = collectionSlug
      // No sort chosen: keep the order the owner arranged.
      if (!params.get('sort')) delete out.sort
    }
    if (filters.q) out.q = filters.q
    if (filters.category) out.category = filters.category
    if (filters.sizes.length) out.size = filters.sizes.join(',')
    if (filters.colors.length) out.color = filters.colors.join(',')
    if (filters.maxPrice) out.max_price = filters.maxPrice
    return out
  }, [filters, collectionSlug, params])

  useEffect(() => { fetchCategories() }, [fetchCategories])

  useEffect(() => {
    fetchProducts({ ...query, page: 1 })
  }, [query, fetchProducts, epoch])

  useEffect(() => {
    setCollection(null)
    if (!collectionSlug) return
    apiClient.get(`/content/collections/${collectionSlug}`)
      .then(({ data }) => setCollection(data))
      .catch(() => setCollection({ missing: true }))
  }, [collectionSlug, epoch])

  // Sizes and colours on offer depend on the category being browsed.
  useEffect(() => {
    apiClient
      .get('/products/facets', { params: filters.category ? { category: filters.category } : {} })
      .then(({ data }) => setFacets(data))
      .catch(() => {}) // filters are an enhancement; the grid works without them
  }, [filters.category])

  const flatCategories = useMemo(
    () => categories.flatMap((c) => [c, ...(c.children || [])]),
    [categories],
  )
  const categoryName = flatCategories.find((c) => c.slug === filters.category)?.name

  const active = [
    filters.q && { key: 'q', label: `“${filters.q}”`, clear: { q: '' } },
    filters.category && { key: 'cat', label: categoryName || filters.category, clear: { category: '' } },
    ...filters.sizes.map((s) => ({ key: `s-${s}`, label: `Size ${s}`, clear: { sizes: filters.sizes.filter((x) => x !== s) } })),
    ...filters.colors.map((c) => ({ key: `c-${c}`, label: c, clear: { colors: filters.colors.filter((x) => x !== c) } })),
    filters.maxPrice && { key: 'price', label: `Up to ${inr(filters.maxPrice)}`, clear: { maxPrice: 0 } },
  ].filter(Boolean)
  const clearAll = () => setParams(filters.sort !== 'newest' ? { sort: filters.sort } : {}, { replace: true })

  const title = collection?.name || (filters.q ? `Results for “${filters.q}”` : categoryName || 'All products')
  const panel = <Filters filters={filters} facets={facets} categories={flatCategories} set={set} />

  return (
    <>
      <Seo
        title={collection?.meta_title || collection?.name || categoryName || 'Shop All Products'}
        description={collection?.meta_description || collection?.description || 'Browse the full collection — clothing, accessories and more, with fast delivery across India.'}
        image={collection?.share_image_url || collection?.image_url || undefined}
        breadcrumbs={[
          { name: 'Home', path: '/' },
          { name: 'Shop', path: '/shop' },
          ...(categoryName ? [{ name: categoryName }] : []),
        ]}
      />
      <Container className="pb-16">
        <PageTitle
          title={title}
          subtitle={collection?.sale_percent
            ? `${collection.description ? `${collection.description} · ` : ''}${Math.round(collection.sale_percent)}% off everything in this collection`
            // (a blank line while a collection loads, so its description does not push the grid down)
            : collection ? collection.description : collectionSlug ? ' ' : undefined}
          crumbs={[{ label: 'Home', to: '/' }, { label: 'Shop', to: collectionSlug ? '/shop' : undefined }, ...(collectionSlug ? [{ label: title }] : [])]}
        />

        <div className="grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
          <aside className="hidden lg:block" aria-label="Filters">
            <div className="sticky top-28">{panel}</div>
          </aside>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted" aria-live="polite">
                {loading ? 'Loading products…' : `${total.toLocaleString('en-IN')} product${total === 1 ? '' : 's'}`}
              </p>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setDrawerOpen(true)}>
                  <IconAdjustmentsHorizontal size={16} />
                  Filters{active.length > 0 && ` (${active.length})`}
                </Button>
                <div className="w-48">
                  <Select aria-label="Sort by" value={filters.sort} onChange={(e) => set({ sort: e.target.value })}>
                    {SORTS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </Select>
                </div>
              </div>
            </div>

            {active.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {active.map((f) => (
                  <button
                    key={f.key} type="button" onClick={() => set(f.clear)}
                    className="inline-flex items-center gap-1.5 rounded-full bg-fill pl-3 pr-2 py-1.5 text-xs font-medium text-fg hover:bg-fill-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    {f.label}
                    <IconX size={12} aria-hidden="true" />
                    <span className="sr-only">Remove filter</span>
                  </button>
                ))}
                <button type="button" onClick={clearAll} className="text-xs font-medium text-muted underline underline-offset-2 hover:text-fg">
                  Clear all
                </button>
              </div>
            )}

            <div className="mt-6">
              {loading ? (
                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8 sm:gap-x-6">
                  {Array.from({ length: 8 }).map((_, i) => <ProductCardSkeleton key={i} />)}
                </div>
              ) : error ? (
                <ErrorState message="We could not load the products." onRetry={() => fetchProducts({ ...query, page: 1 })} />
              ) : products.length === 0 ? (
                <EmptyState
                  icon={IconSearchOff}
                  title="Nothing matches"
                  hint={active.length ? 'Try removing a filter or two.' : 'There are no products here yet. Please check back soon.'}
                  action={active.length > 0 && <Button variant="secondary" onClick={clearAll}>Clear all filters</Button>}
                />
              ) : (
                <>
                  <ul className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8 sm:gap-x-6">
                    {products.map((p, i) => <li key={p.id}><ProductCard product={p} priority={i < 4} /></li>)}
                  </ul>
                  {page < pages && (
                    <div className="mt-12 flex flex-col items-center gap-3">
                      <p className="text-xs text-muted">Showing {products.length} of {total}</p>
                      <Button
                        variant="secondary" disabled={loadingMore}
                        onClick={() => fetchProducts({ ...query, page: page + 1 }, true)}
                      >
                        {loadingMore ? 'Loading…' : 'Load more'}
                      </Button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </Container>

      <Drawer
        open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Filters"
        footer={
          <Button full onClick={() => setDrawerOpen(false)}>
            Show {total.toLocaleString('en-IN')} product{total === 1 ? '' : 's'}
          </Button>
        }
      >
        {panel}
      </Drawer>
    </>
  )
}
