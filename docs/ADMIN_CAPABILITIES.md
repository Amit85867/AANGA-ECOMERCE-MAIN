# What the store owner can do from the admin dashboard

The first table is the state after Round 3. The second is the audit taken
before anything was built, kept for reference.

Roles: **Owner** (everything), **Manager** (everything except Store settings,
Staff, Demo content, System health and "Other text"), **Staff** (products,
categories, media library, orders, returns). The server enforces this on every
admin route; the menu only hides what a role cannot use.

## Now

| Area | What the owner can do | Missing |
|---|---|---|
| Staff and roles | **Staff**: add a person with a role (a one-time password is shown once), change role, deactivate / reactivate, reset password, remove. The last Owner cannot be removed, demoted or deactivated. Every change is in the audit log. | — (No invitation email is sent: the Owner passes the one-time password on. Listed under "Left for the owner" in PROGRESS.md.) |
| Customers | **Customers**: search and filter, detail with lifetime spend, orders, returns, reviews and addresses, block / unblock, export the filtered list as CSV (names, contact details, order totals only). | — |
| Store settings | **Store settings**: name, tagline, logo, favicon, GSTIN, contact email / phone / address, WhatsApp, social links, shipping fee, free-shipping threshold, cash on delivery on/off, return window, default search title / description / share image. Validated, and live on save. | — |
| Homepage | **Homepage**: reorder sections, show / hide them, edit their headings, choose the collection for the featured section. "Edit content" jumps to the screen for each section's content. | — |
| Navigation | **Menus**: header links and footer links (in columns): add, edit, reorder, hide, remove. A header link to a category shows its sub-categories as a drop-down. | — |
| Pages | **Pages**: About, Contact, FAQ introduction, Shipping, Returns, Privacy, Terms, with a rich-text editor and search / sharing fields. Content is sanitised on the server. **FAQ**: add, edit, reorder, hide and remove questions. | — |
| Collections | **Collections**: create, pick and order products, picture, search fields; each has its own page and can be used on the home page, in menus, slides and campaigns. | — |
| Campaigns | **Campaigns**: name, start and end in IST, announcement, hero slides, promo banners, featured collection, optional sale discount, coupons, festive decoration with four accent presets, countdown. Starts and reverts by the clock, Preview, End now, overlap rejected. | — |
| Media | **Media library**: upload several images, search, description and source note, "where it is used", delete only when unused. Every image field has "From library". | — |
| Products and categories | As before, plus fabric and care details, search title / description and share image per product. | — |
| Orders, returns, refunds | Unchanged: list, detail, status changes under transition rules, returns desk, settlements. | — |
| Coupons, offers, reviews | Unchanged, and a coupon can now belong to a campaign. | — |
| Inquiries, messages, newsletter | Unchanged. | — |
| System | Unchanged: integration health, maintenance mode, audit log. | — |
| SEO | Per product, page and collection: title, description, share image. Store-wide defaults in Store settings. `sitemap.xml` includes collections and owner-written pages. | — |
| Help | **Help** in the sidebar shows `docs/OWNER_GUIDE.md`. | — |
| Demo content | **Demo content**: see what is tagged as demo, switch demo mode on to tag what you add, remove all of it with a typed confirmation. Also `flask remove-demo-content`. | — |

## Before Round 3 (the audit)

| Area | What the owner could do | Missing |
|---|---|---|
| Staff and roles | Master admin could create and delete admins. Two roles existed in data (`master`, `staff`) but both could use every screen except admin management and maintenance mode. | No Manager role. Permissions not enforced per area on the server. No edit, deactivate or password reset. Nothing stopped the last master being deleted by another master. |
| Customers | List with search and filters, detail with addresses and last 10 orders, block / unblock, change account type. | No returns, reviews or lifetime spend on the detail page. No CSV export. |
| Store settings | A generic key/value screen whose keys were seeded by a migration. Maintenance mode on the System page. | No fixed set of store fields. Shipping fee (₹49), free-shipping threshold (₹999), COD availability and the 7-day return window were constants in code. Logo and favicon were files in the build. |
| Homepage | Edit the content of hero banners, announcements, promo banners, testimonials, feature cards. | Section order and visibility fixed in code. No collection could be chosen for the featured products. |
| Navigation | — | Header menu and footer links were written in code. |
| Pages | — | About, Contact, FAQ, Returns, Privacy and Terms were written in code. No Shipping page. FAQ was a hard-coded list. |
| Collections | Categories only. | No hand-picked collections. |
| Campaigns | Banners, announcements and offers each had their own start / end dates. | Nothing tied them together; no sale pricing, decoration, countdown, preview or overlap check. |
| Media | Upload an image from inside each form. | No library: an uploaded image could not be found again, reused, or checked for where it was used. |
| Products and categories | Full create / edit / deactivate, variants, stock, images. | No per-product meta title, description or share image. |
| SEO | `sitemap.xml` and `robots.txt`; page titles set in code. | No owner-editable meta; sitemap had no collections or CMS pages. |
| Help | — | No owner documentation. |
| Demo content | — | No way to tell demo data from real data or to remove it. |
