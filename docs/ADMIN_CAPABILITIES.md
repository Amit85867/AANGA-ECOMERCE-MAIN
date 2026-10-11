# What the store owner can do from the admin dashboard

Audit taken at the start of Round 3 (before anything was built). "Missing" is
what a non-technical owner could not do without a developer.

| Area | What the owner can do | Missing |
|---|---|---|
| Staff and roles | Master admin can create and delete admins. Two roles exist in data (`master`, `staff`) but both can use every screen except admin management, maintenance mode. | No Manager role. Permissions are not enforced per area on the server. No edit, deactivate or password reset. Nothing stops the last master being deleted by another master. |
| Customers | List with search and filters, detail with addresses and last 10 orders, block / unblock, change account type. | No returns, reviews or lifetime spend on the detail page. No CSV export. |
| Store settings | A generic key/value screen ("Site settings") whose keys were seeded by a migration. Maintenance mode on the System page. | No fixed set of store fields. Shipping fee (₹49), free-shipping threshold (₹999), COD availability and the 7-day return window are constants in code. Logo and favicon are files in the build. |
| Homepage | Edit the content of hero banners, announcements, promo banners, testimonials, feature cards. | Section order and visibility are fixed in code. Featured products are whatever is flagged "featured"; no collection can be chosen. |
| Navigation | — | Header menu and footer links are written in code. |
| Pages | — | About, Contact, FAQ, Shipping, Returns, Privacy and Terms are written in code. No Shipping page exists. FAQ is a hard-coded list. |
| Collections | Categories only. | No hand-picked collections. |
| Campaigns | Individual banners, announcements and offers each have their own start / end dates. | Nothing ties them together, no sale pricing, no decoration, no countdown, no preview, no overlap check. |
| Media | Upload an image from inside each form; it is resized to 480 / 800 / 1400 px. | No library: an uploaded image cannot be found again, reused, or checked for where it is used. |
| Products and categories | Full create / edit / deactivate, variants, stock, images. | No per-product meta title, description or share image. |
| Orders, returns, refunds | List, detail, status changes under transition rules, tracking events, returns desk with refunds and restock, settlements view. | — |
| Coupons, offers, reviews | Create / edit / delete coupons and offers; remove reviews. | Coupons cannot be tied to a campaign. |
| Inquiries, messages, newsletter | Read and update status; export subscriber list. | — |
| System | Health of every integration, maintenance mode, audit log of every admin change and sign-in. | — |
| SEO | `sitemap.xml` and `robots.txt` generated; page titles set in code. | No owner-editable meta for products or pages; sitemap has no collections or CMS pages. |
| Help | — | No owner documentation. |
| Demo content | — | No way to tell demo data from real data or to remove it. |

The second half of this file is rewritten once the gaps are closed.
