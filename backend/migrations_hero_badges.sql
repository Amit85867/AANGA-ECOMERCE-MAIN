-- Migration: hero banner decorative badges
--
-- Optional overlays on the homepage hero visual, matching the reference design:
--   * a "pill"  — small label + value (e.g. "This Season" / "Summer Edit '26")
--   * a "chip"  — big value + small label (e.g. "40%" / "Off Sale Items")
--
-- All nullable; existing banners are unaffected (badges simply don't render).
-- Apply to the live Supabase database. Safe to run more than once.

ALTER TABLE public.hero_banners ADD COLUMN IF NOT EXISTS pill_label text;
ALTER TABLE public.hero_banners ADD COLUMN IF NOT EXISTS pill_value text;
ALTER TABLE public.hero_banners ADD COLUMN IF NOT EXISTS chip_value text;
ALTER TABLE public.hero_banners ADD COLUMN IF NOT EXISTS chip_label text;
