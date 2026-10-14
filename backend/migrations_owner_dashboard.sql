-- Migration: owner dashboard (Round 3)
--
-- Collections, campaigns, the homepage builder, editable navigation, pages and
-- FAQ, the media library, SEO fields and the "demo content" flag.
--
-- Applied by scripts/render_bootstrap_db.sh. Safe to run more than once: every
-- statement is guarded. It inserts no rows — defaults (homepage sections,
-- menus, the list of pages) are created by the application the first time
-- they are read, so an empty database and a test database behave the same.

-- ── Demo content flag ────────────────────────────────────────
ALTER TABLE public.products      ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.categories    ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.hero_banners  ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.promo_banners ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.announcements ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.testimonials  ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.features      ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.coupons       ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.offers        ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.users         ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE public.admins        ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;

-- ── Product SEO and care details ─────────────────────────────
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS care_details text;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_title text;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS meta_description text;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS share_image_url text;

-- ── Collections ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.collections (
    id bigserial PRIMARY KEY,
    name text NOT NULL,
    slug text NOT NULL UNIQUE,
    description text,
    image_url text,
    is_active boolean NOT NULL DEFAULT true,
    meta_title text,
    meta_description text,
    share_image_url text,
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.collection_products (
    collection_id bigint NOT NULL REFERENCES public.collections(id) ON DELETE CASCADE,
    product_id bigint NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    sort_order integer NOT NULL DEFAULT 0,
    PRIMARY KEY (collection_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_collection_products_product ON public.collection_products (product_id);

-- ── Campaigns ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.campaigns (
    id bigserial PRIMARY KEY,
    name text NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    -- Set by "End now". A campaign is live while starts_at <= now < ends_at
    -- and this is empty.
    ended_at timestamptz,
    announcement_text text,
    announcement_highlight text,
    announcement_link_url text,
    announcement_link_text text,
    collection_id bigint REFERENCES public.collections(id) ON DELETE SET NULL,
    sale_percent numeric(4,1),
    decoration_enabled boolean NOT NULL DEFAULT false,
    accent_preset text NOT NULL DEFAULT 'marigold',
    show_countdown boolean NOT NULL DEFAULT false,
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_campaign_dates CHECK (ends_at > starts_at),
    CONSTRAINT ck_campaign_sale CHECK (sale_percent IS NULL OR (sale_percent > 0 AND sale_percent <= 90))
);
CREATE INDEX IF NOT EXISTS idx_campaigns_window ON public.campaigns (starts_at, ends_at);

-- Slides and promo banners made for a campaign disappear with it; a coupon
-- outlives it (orders reference coupons) and is simply no longer usable.
ALTER TABLE public.hero_banners  ADD COLUMN IF NOT EXISTS campaign_id bigint REFERENCES public.campaigns(id) ON DELETE CASCADE;
ALTER TABLE public.promo_banners ADD COLUMN IF NOT EXISTS campaign_id bigint REFERENCES public.campaigns(id) ON DELETE CASCADE;
ALTER TABLE public.coupons       ADD COLUMN IF NOT EXISTS campaign_id bigint REFERENCES public.campaigns(id) ON DELETE SET NULL;

-- ── Homepage builder ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.homepage_sections (
    id bigserial PRIMARY KEY,
    key text NOT NULL UNIQUE,
    title text,
    subtitle text,
    is_visible boolean NOT NULL DEFAULT true,
    sort_order integer NOT NULL DEFAULT 0,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ── Navigation ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.nav_links (
    id bigserial PRIMARY KEY,
    location text NOT NULL,
    group_name text,
    label text NOT NULL,
    url text NOT NULL,
    sort_order integer NOT NULL DEFAULT 0,
    is_visible boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_nav_location CHECK (location IN ('header', 'footer'))
);
CREATE INDEX IF NOT EXISTS idx_nav_links_location ON public.nav_links (location, sort_order);

-- ── Pages and FAQ ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.cms_pages (
    id bigserial PRIMARY KEY,
    slug text NOT NULL UNIQUE,
    title text NOT NULL,
    -- Sanitised on the server before it is stored (app/services/sanitize.py).
    body_html text NOT NULL DEFAULT '',
    meta_title text,
    meta_description text,
    share_image_url text,
    is_demo boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.faq_items (
    id bigserial PRIMARY KEY,
    question text NOT NULL,
    answer text NOT NULL,
    sort_order integer NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true,
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ── Media library ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.media_assets (
    id bigserial PRIMARY KEY,
    url text NOT NULL UNIQUE,
    filename text,
    alt_text text,
    width integer,
    height integer,
    size_bytes integer,
    -- Where the picture came from and under what licence, for the owner's records.
    source_note text,
    is_demo boolean NOT NULL DEFAULT false,
    uploaded_by uuid REFERENCES public.admins(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_media_assets_created ON public.media_assets (created_at DESC);
