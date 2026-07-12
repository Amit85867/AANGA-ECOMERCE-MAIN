-- ============================================================
-- AANGA CMS Tables — Run this in Supabase SQL Editor
-- ============================================================

-- 1. Hero Banners (homepage slider)
CREATE TABLE IF NOT EXISTS hero_banners (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    subtitle    TEXT,
    description TEXT,
    image_url   TEXT NOT NULL,
    mobile_image_url TEXT,
    link_url    TEXT,
    link_text   TEXT,
    secondary_link_url TEXT,
    secondary_link_text TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Announcements (top bar strip)
CREATE TABLE IF NOT EXISTS announcements (
    id              BIGSERIAL PRIMARY KEY,
    text            TEXT NOT NULL,
    highlight_text  TEXT,
    link_url        TEXT,
    link_text       TEXT,
    bg_color        TEXT NOT NULL DEFAULT '#0A0A0A',
    text_color      TEXT NOT NULL DEFAULT '#ffffff',
    highlight_color TEXT NOT NULL DEFAULT '#D4AF37',
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    starts_at       TIMESTAMPTZ,
    ends_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Promo Banners (mid-page sale section)
CREATE TABLE IF NOT EXISTS promo_banners (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    subtitle    TEXT,
    description TEXT,
    badge_text  TEXT,
    image_url   TEXT,
    link_url    TEXT,
    link_text   TEXT,
    items       JSONB,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Site Settings (key-value config)
CREATE TABLE IF NOT EXISTS site_settings (
    id          BIGSERIAL PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,
    value       TEXT NOT NULL DEFAULT '',
    label       TEXT,
    group_name  TEXT NOT NULL DEFAULT 'general',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Seed: Hero Banner (matches the current homepage hero section)
-- ============================================================
INSERT INTO hero_banners (title, subtitle, description, image_url, link_url, link_text, secondary_link_url, secondary_link_text, sort_order, is_active) VALUES
    (
        E'Wear the\nStory of\nIndia''s Finest',
        'Summer Collection 2026',
        'Premium quality clothing for men, women & kids. From everyday essentials to seasonal collections — crafted for those who wear their confidence.',
        '/static/uploads/hero-placeholder.webp',
        '/shop',
        'Shop Now',
        '/offers',
        'View Offers',
        0,
        TRUE
    );

-- ============================================================
-- Seed: Announcement Bar (matches current top strip)
-- ============================================================
INSERT INTO announcements (text, highlight_text, link_url, link_text, bg_color, text_color, highlight_color, is_active) VALUES
    (
        'Summer Sale Live',
        'Free shipping on orders above ₹999',
        '/offers',
        'Shop Now',
        '#0A0A0A',
        '#ffffff',
        '#D4AF37',
        TRUE
    );

-- ============================================================
-- Seed: Promo Banner (matches current mid-page sale section)
-- ============================================================
INSERT INTO promo_banners (title, subtitle, description, badge_text, link_url, link_text, items, is_active) VALUES
    (
        'Season Sale is Live Now',
        'Sale',
        'Up to 50% off on selected styles. Shop men''s, women''s, and kids'' clothing before stocks run out.',
        'Limited Time',
        '/offers',
        'Shop the Sale',
        '[{"pct": "50%", "label": "On Jackets"}, {"pct": "40%", "label": "On Jeans"}, {"pct": "35%", "label": "On T-Shirts"}, {"pct": "30%", "label": "On Innerwear"}]'::JSONB,
        TRUE
    );

-- ============================================================
-- Seed: Site Settings (all configurable values)
-- ============================================================
INSERT INTO site_settings (key, value, label, group_name) VALUES
    ('store_name',              'AANGA',                                    'Store Name',               'general'),
    ('store_tagline',           'Wear the Story of India''s Finest',        'Store Tagline',            'general'),
    ('store_email',             'support@aanga.in',                         'Support Email',            'contact'),
    ('store_phone',             '+91 9876543210',                           'Support Phone',            'contact'),
    ('store_address',           '',                                         'Store Address',            'contact'),
    ('gst_rate',                '0.05',                                     'GST Rate (decimal)',       'tax'),
    ('free_shipping_threshold', '999',                                      'Free Shipping Above (₹)',  'shipping'),
    ('delivery_charge',         '49',                                       'Delivery Charge (₹)',      'shipping'),
    ('instagram_url',           '',                                         'Instagram URL',            'social'),
    ('facebook_url',            '',                                         'Facebook URL',             'social'),
    ('twitter_url',             '',                                         'Twitter / X URL',          'social'),
    ('youtube_url',             '',                                         'YouTube URL',              'social'),
    ('whatsapp_number',         '',                                         'WhatsApp Number',          'social'),
    ('happy_customers',         '50K+',                                     'Happy Customers Count',    'stats'),
    ('styles_available',        '1200+',                                    'Styles Available Count',   'stats'),
    ('wholesale_partners',      '500+',                                     'Wholesale Partners Count', 'stats')
ON CONFLICT (key) DO NOTHING;
