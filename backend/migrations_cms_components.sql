-- ============================================================
-- AANGA CMS — Testimonials, Features & Homepage Text
-- Run this in Supabase SQL Editor (after migrations_cms.sql)
-- ============================================================

-- 1. Testimonials (homepage customer reviews)
CREATE TABLE IF NOT EXISTS testimonials (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    location    TEXT,
    rating      SMALLINT NOT NULL DEFAULT 5,
    quote       TEXT NOT NULL,
    avatar_url  TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Features ("Why Choose AANGA" cards)
CREATE TABLE IF NOT EXISTS features (
    id          BIGSERIAL PRIMARY KEY,
    icon        TEXT,
    title       TEXT NOT NULL,
    description TEXT,
    image_url   TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Seed example testimonials (edit/replace from the admin panel)
-- ============================================================
INSERT INTO testimonials (name, location, rating, quote, sort_order) VALUES
    ('Rahul Kumar',  'Patna, Bihar',        5, 'Ordered 3 shirts for a wedding. The quality blew my mind — exactly like expensive branded stores but at half the price.', 0),
    ('Priya Singh',  'Muzaffarpur, Bihar',  5, 'I run a small clothing shop and AANGA is my go-to wholesale supplier. Great bulk pricing and fresh collections always.', 1),
    ('Arjun Verma',  'Ranchi, Jharkhand',   5, 'Bought a hoodie and jacket combo. Arrived in 4 days. Feels like a Nike product at a fraction of the cost.', 2),
    ('Neha Gupta',   'Gaya, Bihar',         4, 'Good quality and fast delivery. Sizing ran a little large for me but exchange was smooth.', 3),
    ('Sample Review','Your City',           3, 'This is an example review below 4 stars — it will appear under "View more reviews" on the homepage. Edit or delete it from the admin panel.', 4);

-- ============================================================
-- Seed example features (edit/replace from the admin panel)
-- ============================================================
INSERT INTO features (icon, title, description, sort_order) VALUES
    ('shield-check', 'Premium Quality',  'Every garment passes rigorous quality checks. Durable fabrics, fine stitching — built to last.', 0),
    ('truck',        'Fast Delivery',    'Doorstep delivery across India. Free shipping on orders above ₹999.', 1),
    ('refresh',      'Easy Returns',     'Not happy? Return within 7 days, no questions asked. Hassle-free process.', 2),
    ('headset',      'Customer Support', 'Our team is always here. Call, WhatsApp, or email — we respond within hours.', 3);

-- ============================================================
-- Seed homepage text settings (group: content)
-- ============================================================
INSERT INTO site_settings (key, value, label, group_name) VALUES
    ('section_categories_tag',   'Explore',              'Categories — small tag',      'content'),
    ('section_categories_title', 'Shop by Category',     'Categories — title',          'content'),
    ('section_products_tag',     'Trending Now',         'Products — small tag',        'content'),
    ('section_products_title',   'Best Sellers',         'Products — title',            'content'),
    ('why_choose_tag',           'Our Promise',          'Why Choose — small tag',      'content'),
    ('why_choose_title',         'Why Choose AANGA',     'Why Choose — title',          'content'),
    ('testimonials_tag',         'Testimonials',         'Testimonials — small tag',    'content'),
    ('testimonials_title',       'What Customers Say',   'Testimonials — title',        'content'),
    ('newsletter_heading',       'Stay in Style',        'Newsletter — heading',        'content'),
    ('newsletter_subtitle',      'Get early access to new collections, exclusive deals, and seasonal lookbooks.', 'Newsletter — subtitle', 'content'),
    ('footer_tagline',           'Bihar''s premium fashion destination for men, women & kids. Wholesale and retail clothing with 1,200+ styles.', 'Footer — tagline', 'content')
ON CONFLICT (key) DO NOTHING;
