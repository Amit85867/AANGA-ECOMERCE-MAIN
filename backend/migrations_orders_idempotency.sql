-- Migration: order integrity guards (Phase 1c + 1e)
--
-- Applied by scripts/render_bootstrap_db.sh (fresh load and --migrate) and,
-- when moving data off Supabase, by db/migrate-from-supabase.ps1 after the
-- restore. The application no longer runs on a Supabase database, so there is
-- nothing to apply there by hand. Safe to run more than once (IF NOT EXISTS
-- guards). No ON CONFLICT seed data here.
--
-- 1c. A partial UNIQUE index on payment_ref makes prepaid order creation
--     race-proof: a concurrent double-verify can no longer create two orders
--     for one captured payment (app-level idempotency alone has a
--     check-then-insert race).
--
-- 1e. idempotency_key + its partial UNIQUE index make a double-submitted COD
--     checkout resolve to a single order.
--
-- NOTE: if the orders table already contains duplicate payment_ref values the
-- CREATE UNIQUE INDEX will fail. Check first with:
--   SELECT payment_ref, count(*) FROM public.orders
--   WHERE payment_ref IS NOT NULL GROUP BY payment_ref HAVING count(*) > 1;

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_payment_ref
    ON public.orders USING btree (payment_ref)
    WHERE (payment_ref IS NOT NULL);

CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_idempotency_key
    ON public.orders USING btree (idempotency_key)
    WHERE (idempotency_key IS NOT NULL);
