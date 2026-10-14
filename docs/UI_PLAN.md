# UI plan — storefront modernisation

**Status: waiting for approval. Nothing in this plan has been built.**
One decision is needed first (section 1); everything after it follows from the answer.

## 1. Decision needed: which look is "the existing theme"?

The storefront currently has **two** visual systems live at the same time, because
an earlier redesign was started and stopped part-way.

| | A — "Editorial" (the redesign in progress) | B — "Warm" (the original) |
|---|---|---|
| Colours | near-black `#191c1e` on cool grey `#f8f9fb`, pink accent `#f53765` | ink `#0a0a0a` on cream `#fafaf8`, gold accent `#c8963e`, maroon `#8b1a1a` |
| Headings | Poppins, bold, tight tracking | Playfair Display (serif) |
| Shape | 16–24px rounded cards, very soft shadows | square corners, hairline borders |
| Used on today | navbar, footer, announcement bar, product card, **product detail page** | home, shop, cart, checkout, account, sign-in pages, order tracking, wishlist, offers, contact, wholesale, static pages, admin |
| Size in code | 240 class references | 1,299 class references (608 of them in admin) |

So a shopper today sees the Editorial navbar and product cards on top of Warm page
bodies, then lands on an Editorial product page, then a Warm cart. The mismatch is
the single biggest thing making the site look unfinished.

Your instruction was to keep the existing theme and to "continue the redesign from
UI3 (product detail) onward". Those point in different directions for most pages:

- **Option A — finish the Editorial system (recommended).** This is the redesign
  that "UI3 onward" refers to; its tokens, buttons, inputs, chips and cards already
  exist and product detail is already built on it. The remaining customer pages move
  from gold/serif to black/pink/Poppins. The AANGA logo and name do not change.
  Admin keeps its current look (dark sidebar, gold accent) — it is a separate tool
  and was just rebuilt in Phase 3.
- **Option B — keep the Warm look everywhere.** The gold/serif pages stay as the
  brand, and the navbar, footer, product card and product detail page are restyled
  *back* to match them. Less visual change for returning visitors; the Editorial work
  already done is partly discarded.

Either way the result is one consistent system. I recommend A because it is where
the existing component library already is and it discards no finished work.

A contrast note that applies to both: neither accent passes WCAG AA as small text
(gold `#c8963e` on cream is 2.5:1, pink `#f53765` on white is 3.7:1; AA needs
4.5:1). Under either option the accent is kept for large text, icons and
decoration, and the small gold labels on today's Warm pages (the 10px uppercase
section tags) move to the body text colour.

## 2. Frozen tokens

These are the values in `frontend/src/index.css` today. Whichever option is chosen,
its set is frozen: this work changes layout, spacing, hierarchy, states and motion,
and does not add, remove or alter a colour, font or radius.

**Editorial (Option A)**

| Token | Value | Use |
|---|---|---|
| `bg` / `card` / `fill` / `fill-strong` | `#f8f9fb` / `#ffffff` / `#f2f4f6` / `#e7e8ea` | canvas, cards, inputs, pressed |
| `fg` / `muted` / `subtle` | `#191c1e` / `#444748` / `#747878` | text: primary, secondary, tertiary |
| `hairline` | `#c4c7c7` | borders, dividers |
| `primary` / `on-primary` | `#000000` / `#ffffff` | solid buttons |
| `accent` / `accent-soft` | `#f53765` / `#ffd9dc` | sale tags, active states — sparingly |
| `danger` / `danger-soft` | `#ba1a1a` / `#ffdad6` | errors |
| `font-display` / `font-sans` | Poppins 500–700 / Inter 300–700 | headings / body |
| `rounded-card` / `rounded-block` | 16px / 24px | cards and inputs / banners |
| `shadow-card` / `shadow-lift` | `0 10px 40px rgb(0 0 0 / .04)` / `0 18px 50px rgb(0 0 0 / .08)` | resting / hover |

**Warm (Option B)**

| Token | Value |
|---|---|
| `ink` / `paper` / `cream` / `surface` | `#0a0a0a` / `#fafaf8` / `#f5f0e8` / `#f2ede5` |
| `gold` / `gold-light` | `#c8963e` / `#e8b96a` |
| `maroon` / `maroon-light` | `#8b1a1a` / `#c0392b` |
| `gray` / `line` | `#6b6b6b` / `#e8e4dc` |
| `font-serif` / `font-sans` | Playfair Display / Inter |
| radius / shadow | none (square corners, hairline borders) |

**Brand assets (both):** `logo-main.png` (mark), `logo-title.png` (wordmark),
`favicon.svg` / `favicon.png`. Icons: Tabler. Currency: ₹ INR throughout.

One housekeeping change is included: 57 uses of the literal `#C8963E` and 24 of
`#b88534` in the admin become the `gold` token, so the value lives in one place. The
colour itself does not change.

## 3. What is wrong today (measured)

| Finding | Count | Effect |
|---|---|---|
| Images with no `width` / `height` | 23 of 23 | page jumps as images load (layout shift) |
| Images lazy-loaded | 2 of 23 | every product image downloads up front |
| Text set below 12px (`text-[9px]`–`text-[11px]`) | 161 uses | hard to read, fails on mobile |
| `outline-none` vs `focus-visible` styles | 54 vs 12 | keyboard users cannot see where they are |
| Account layout is a fixed `240px + 1fr` grid | 1 | unusable below ~700px wide |
| Native `<select>` / range input styled per page | ~15 | inconsistent controls |
| Backend features with **no screen** | 4 | customers cannot cancel an order, write or read a review, see their returns, or edit an address |

## 4. Shared components

Built once on the frozen tokens, in `frontend/src/components/ui/`, each with hover,
focus-visible, disabled and loading states, and documented on the existing
`/style-guide` page.

Already exist (to be completed, not replaced): `Button`, `Input`, `Chip`, `Card`,
`ProductCard`, `Toast`, `PageHeader`.

To add: `Select`, `Textarea`, `Checkbox` / `Radio`, `QuantityStepper`, `Modal`
(focus-trapped, Esc to close), `Drawer` (mobile filters and menu), `Badge`,
`Skeleton`, `EmptyState`, `ErrorState`, `Pagination` / load-more, `Breadcrumbs`,
`Rating` (display and input), `Price` (MRP / selling / % off, one format everywhere),
`Tabs`, `Stepper` (checkout progress), `Table` (orders).

## 5. Page by page

In build order. Each page is finished — responsive from 360px, keyboard-usable,
loading / empty / error states, no layout shift — before the next starts.

1. **Shop / listing.** Filters in a sticky sidebar on desktop and a drawer on
   mobile; active filters shown as removable chips; filter state in the URL so a
   filtered view can be shared; skeleton grid; "no results" with a clear-filters
   action. *Size and colour filters need a small backend addition* (the API filters
   by category, price and search only) — included.
2. **Product detail** (already Editorial). Add the reviews section — rating
   summary, list, and "write a review" for signed-in buyers — and tidy the delivery
   check. Wire both review endpoints, which have no screen today.
3. **Cart.** Line items with stepper and remove, coupon field with inline result,
   order summary that stays in view; clear empty state.
4. **Checkout and order success.** Three visible steps (address → payment →
   review); address cards with add and edit; a proper confirmation page after
   paying. Online payment shows as unavailable, not broken, when Razorpay is not
   configured. The earlier design's "delivery method" step is left out — the store
   has one flat rate — and so is "saved cards" (Razorpay holds cards).
5. **Account.** Responsive layout (sidebar becomes tabs on mobile). Orders with
   status and a **Cancel order** button where allowed; order detail with timeline;
   **My returns**; addresses with **edit**; profile and password.
6. **Sign in, register, forgot and reset password.** One consistent card; password
   rules shown before submit; phone-OTP hidden while no SMS provider is configured.
7. **Home.** Section rhythm and spacing, image sizing, real headings hierarchy.
8. **Remaining pages.** Order tracking, wishlist, offers, contact, wholesale, about,
   FAQ, policies, 404, maintenance.
9. **Admin shell.** Sidebar grouped into sections (Catalogue, Sales, Content,
   System) — it is a flat list of 22 links today — with a collapsed mobile state.
   Colours stay as they are.
10. **Clean-up.** Remove the unused palette and font once nothing references it
    (one fewer web font to download).

## 6. Standards and how each is checked

| Standard | Check |
|---|---|
| Responsive 360px → 1920px | each page viewed at 360, 768, 1280, 1920 in the browser walkthrough |
| Keyboard access, visible focus | tab through every page; no `outline-none` without a `focus-visible` replacement |
| WCAG AA contrast | every text/background token pair computed; pairs that fail are restricted to large text |
| 4 / 8px spacing scale | only Tailwind scale steps; arbitrary pixel values removed |
| No layout shift | every image has `width` and `height`; skeletons match final dimensions |
| Images | `loading="lazy"` below the fold, `fetchpriority="high"` on the hero |
| Lighthouse mobile ≥ 90 performance, ≥ 95 accessibility | run on home, listing and product pages against a production build; scores recorded in `PROGRESS.md` |

## 7. Not in scope

- New colours, fonts, logo or brand name.
- New product features beyond the four missing screens in section 3.
- A paid SMS provider for phone-OTP sign-in (the option is hidden instead).
- Product photography — pages are built to the images that exist.

## 8. What I need from you

1. **Option A or B** (section 1).
2. Confirm the build order in section 5, or say what should come first.
