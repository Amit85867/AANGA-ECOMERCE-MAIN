# Owner guide

This guide explains how to run your store from the admin dashboard. You do not need a developer for anything described here.

## Getting started

1. Go to your store's address followed by `/admin` and sign in with your email and password.
2. The menu on the left is grouped by job: **Sales**, **Catalogue**, **Marketing**, **Storefront content**, **Inbox** and **Store**.
3. What you see depends on your role. An **Owner** sees everything. A **Manager** sees everything except Store settings, Staff, Demo content and System health. **Staff** see only products, categories, the media library, orders and returns.
4. Changes are live as soon as you save them. There is nothing to publish and nothing to deploy.

> Every change made in the dashboard is recorded in the [Audit log](/admin/audit-log) with who made it and when.

## Add a product

1. Open [Products](/admin/products) and press **Add Product**.
2. Fill in the name, choose a category, and write a description. The web address (slug) is made from the name.
3. Enter the **MRP** and the **selling price**. The selling price cannot be higher than the MRP. The saving shown to customers is worked out for you.
4. Add **Fabric and care** details if you have them. They appear in their own section on the product page.
5. Press **Create**. The page stays open so you can add the rest.
6. Under **Variants**, add each size and colour you sell, with how many you have in stock. A product with no variants cannot be bought.
7. Under **Images**, upload photos or pick them **From library**. The first image is the main one. Portrait photos (3:4) look best.
8. Optional: under **Search and sharing**, write the title and description people see in Google, and choose the picture shown when the link is shared.

To take a product off sale without deleting it, open it and untick **Active**.

## Update stock

1. Open [Products](/admin/products) and open the product.
2. In the **Variants** table, change the number in the stock column and press **Save** on that row.
3. Stock goes down by itself when an order is placed and comes back when an order is cancelled.

## Handle an order

1. Open [Orders](/admin/orders). New orders are at the top with the status **Pending**.
2. Open an order to see what was bought, the address, and how it is being paid for.
3. Move it forward with **Update Status**: Confirmed, Packed, Shipped, Out for delivery, Delivered. The customer sees each step on their order page.
4. Statuses only move forward. A delivered order cannot be moved back, and a cancelled order cannot be reopened.
5. To cancel, choose **Cancelled**. Stock is returned, and if the customer paid online the money is refunded automatically.

> A cash-on-delivery order is marked as paid when you mark it **Delivered**.

## Handle a return

1. A customer asks for a return from their account. It appears under [Returns](/admin/returns).
2. Open the return to see the item and the reason.
3. To accept it, choose **Resolved** and how you are settling it (refund or exchange). Tick **Restock** if the item can be sold again.
4. If the customer paid online, the refund is sent through the payment gateway for you. For cash on delivery, pay the customer yourself and note it.
5. To refuse it, choose **Rejected**.

How long customers have to ask for a return is set under Store settings (see below).

## Change store settings

1. Open [Store settings](/admin/settings). Only the Owner can.
2. **Store**: your store's name, tagline, logo, browser-tab icon and GSTIN.
3. **Contact**: the email, phone and address shown on the Contact page and footer.
4. **Social links**: paste the full address of each profile. Leave one empty to hide its icon.
5. **Shipping and payment**: the shipping fee, the order amount from which shipping is free, whether you accept cash on delivery, and the return window in days.
6. **Search and sharing**: the title and description used when a page has none of its own.
7. Press **Save settings**. The store uses the new values immediately.

## Arrange the home page

1. Open [Homepage](/admin/homepage).
2. Each row is a section of the home page, top to bottom.
3. Use the **up and down arrows** to change the order.
4. Press **Shown / Hidden** to switch a section on or off.
5. Where a section has a heading, you can change the wording.
6. For **Featured collection**, choose which products to show: a collection you have made, or the products marked "featured".
7. Press **Save homepage**, then **View store** to see it.

To change what is *in* a section, press **Edit content** on its row. That takes you to the right screen: Hero slides, Promo banners, Testimonials, Feature cards or Categories.

## Edit menus

1. Open [Menus](/admin/navigation).
2. **Header menu** is the bar at the top of the store. **Footer links** are grouped into columns.
3. Change a link's text or address, untick **Show** to hide it, use the arrows to reorder, or press the bin to remove it.
4. Press **Add link** for a new one. Addresses on your own store start with `/`, for example `/shop` or `/collections/diwali-edit`.
5. Press **Save menus**.

> A header link to a category, such as `/shop?category=men`, automatically shows that category's sub-categories as a drop-down.

## Edit pages and the FAQ

1. Open [Pages](/admin/pages) and press **Edit** on About, Contact, Shipping, Returns, Privacy or Terms.
2. Type or paste your text. Use the toolbar for headings, bold, italics, lists and links.
3. Press **Save page**, then **View page**.
4. For questions and answers, open [FAQ](/admin/faq). Press **Add question**, or use the pencil to change one and the arrows to reorder.

Only simple formatting is kept. Anything else you paste is removed when you save, to keep your store safe.

## Make a collection

A collection is a group of products you pick by hand, such as "Diwali Edit" or "Workwear Edit".

1. Open [Collections](/admin/collections) and press **New collection**.
2. Give it a name and a short description.
3. On the right, search for products and press **Add**. Use the arrows to put them in order.
4. Press **Create collection**. It now has its own page at `/collections/your-name`.
5. Use it on the home page (Homepage, Featured collection), link to it from a menu or a hero slide, or put it on sale in a campaign.

## Run a sale

The simplest sale is a coupon code.

1. Open [Coupons](/admin/coupons) and press **Add Coupon**.
2. Enter a code such as `WELCOME10`, choose a percentage or a rupee amount, and set a minimum order value if you want one.
3. Set a usage limit and an expiry date so it cannot be used for ever.
4. Press **Create** and share the code. Customers type it in their cart.

To put a group of products on sale for a period, use a campaign, described next.

## Launch a festival campaign

A campaign changes the look of the store, puts a collection on sale and switches coupons on, all for a set period. It starts and stops by itself.

1. First make a collection of the products you want to feature (see above).
2. Open [Campaigns](/admin/campaigns) and press **New campaign**.
3. Enter a name and the **start and end, in Indian time**. To start straight away, leave the start as it is.
4. **Announcement bar**: a greeting and an offer, with a link. Tick the countdown if you want "Ends in..." shown.
5. **Featured collection and sale**: choose the collection and, if you want, a discount percentage. The discount is taken off at the till during the campaign only. Your product prices are not changed.
6. **Festive look**: switch on decoration and choose an accent colour. It adds small accents only. Your store's own colours and fonts stay as they are.
7. Press **Schedule campaign**.
8. Now add **Hero slides** (a picture, headline and button each) and, if you like, a **Promo banner**. They replace the usual ones only while the campaign is live.
9. Under **Coupons**, tick the codes that belong to this campaign, or press **New coupon**. Then press **Save campaign**. These codes work only while the campaign is live.
10. Press **Preview** to see the store as customers will, before it starts. Only you can see the preview.

When the end time arrives, everything goes back to normal by itself. To stop early, press **End now**.

> Only one campaign can run at a time. If the dates overlap another campaign you will be told which one, and nothing is saved until you change them.

## Use the media library

1. Open [Media library](/admin/media). Every picture ever uploaded to the store is here.
2. Press **Upload images** to add several at once. They are resized automatically for phones and large screens.
3. Wherever the dashboard asks for a picture, press **From library** to reuse one instead of uploading it again.
4. Click a picture to add a description, note where it came from, and see **where it is used**.
5. A picture that is in use cannot be deleted. Replace it in the places listed first.

## Add staff

1. Open [Staff](/admin/staff) and press **Add staff member**. Only the Owner can.
2. Enter their name and email and choose a role: **Manager** or **Staff**.
3. Press **Add staff member**. A one-time password is shown once. Copy it and pass it to them privately.
4. To change someone's role, use the drop-down in their row.
5. To stop someone signing in, press **Deactivate**. To give them a new password, press the key.
6. To remove someone completely, press the bin. What they did stays in the audit log.

There must always be at least one Owner, so the last Owner cannot be removed or changed to another role.

## Look after customers

1. Open [Customers](/admin/users). Search by name, email or phone.
2. Open a customer to see how much they have spent, their orders, returns, reviews and addresses.
3. Press **Block User** to stop someone signing in or ordering. Press it again to unblock.
4. Press **Export CSV** to download the list as a spreadsheet. It contains names, contact details and order totals only.

## Remove the demo content

Your store was set up with sample products, pages and customers so you can see how everything works. They are marked with a purple **Demo** label.

1. Open [Demo content](/admin/demo). Only the Owner can.
2. The page lists how many demo items there are of each kind.
3. Press **Remove demo content**, type the confirmation phrase shown, and press **Remove it all**.
4. Everything marked Demo is deleted. Your own products, orders and customers are not touched.

You can also replace demo items one at a time instead: edit a demo product or page and it becomes yours.

> Keep **Demo mode** switched off when you add your real products. While it is on, a purple bar across the top of the dashboard reminds you.

## If something goes wrong

1. **I cannot sign in.** Ask the Owner to reset your password under Staff. If you are the only Owner, your developer can reset it.
2. **A page says I do not have access.** Your role does not include that part of the dashboard. Ask the Owner.
3. **Customers cannot pay online, or the pincode check is missing.** Open [System health](/admin/system). It shows which services are set up and whether they are working.
4. **I need to close the store for a while.** Open [System health](/admin/system) and switch on maintenance mode. Customers see a "back soon" page; the dashboard keeps working.
5. **I want to know who changed something.** Open the [Audit log](/admin/audit-log) and search for it.
