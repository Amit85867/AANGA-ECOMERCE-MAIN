-- Remove the test data created for the local browser walkthrough.
--
-- Everything the walkthrough creates belongs to an account whose email ends in
-- "@local.test" (a domain that can never receive mail), so that suffix is the
-- only thing this script trusts. Run it against the LOCAL database before
-- taking any dump that will be restored elsewhere:
--
--   docker compose -f backend/docker-compose.yml exec -T db \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < backend/db/qa_cleanup.sql
--
-- A database loaded by scripts/render_bootstrap_db.sh starts empty and never
-- contains this data; that script's verification fails if it finds any.
--
-- One transaction: it removes everything or nothing. Stock taken by test
-- orders that were never cancelled is put back.

BEGIN;

CREATE TEMP TABLE qa_users ON COMMIT DROP AS
    SELECT id FROM public.users WHERE email LIKE '%@local.test';

CREATE TEMP TABLE qa_orders ON COMMIT DROP AS
    SELECT id, status FROM public.orders WHERE user_id IN (SELECT id FROM qa_users);

-- Cancelled orders already had their stock restored by the trigger.
UPDATE public.product_variants pv
   SET stock_qty = pv.stock_qty + taken.quantity
  FROM (
        SELECT oi.variant_id, sum(oi.quantity) AS quantity
          FROM public.order_items oi
          JOIN qa_orders o ON o.id = oi.order_id
         WHERE o.status <> 'cancelled'
         GROUP BY oi.variant_id
       ) AS taken
 WHERE pv.id = taken.variant_id;

DELETE FROM public.returns         WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.product_reviews WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.order_tracking  WHERE order_id IN (SELECT id FROM qa_orders);
DELETE FROM public.order_items     WHERE order_id IN (SELECT id FROM qa_orders);
DELETE FROM public.orders          WHERE id IN (SELECT id FROM qa_orders);
DELETE FROM public.wishlist        WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.cart_items      WHERE cart_id IN (SELECT id FROM public.carts WHERE user_id IN (SELECT id FROM qa_users));
DELETE FROM public.carts           WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.addresses       WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.password_resets WHERE user_id IN (SELECT id FROM qa_users);
DELETE FROM public.user_sessions   WHERE user_id IN (SELECT id FROM qa_users);

DELETE FROM public.contact_messages      WHERE email LIKE '%@local.test';
DELETE FROM public.wholesale_inquiries   WHERE email LIKE '%@local.test';
DELETE FROM public.newsletter_subscribers WHERE email LIKE '%@local.test';
DELETE FROM public.admins                WHERE email LIKE '%@local.test';
DELETE FROM public.audit_log             WHERE actor_label LIKE '%@local.test';

DELETE FROM public.users WHERE id IN (SELECT id FROM qa_users);

-- The product and category the admin walkthrough created (slug "qa-walkthrough-…").
-- No order can reference them: the product was deactivated before anyone could buy it.
DELETE FROM public.product_images   WHERE product_id IN (SELECT id FROM public.products WHERE slug LIKE 'qa-walkthrough-%');
DELETE FROM public.product_variants WHERE product_id IN (SELECT id FROM public.products WHERE slug LIKE 'qa-walkthrough-%');
DELETE FROM public.products         WHERE slug LIKE 'qa-walkthrough-%';
DELETE FROM public.categories       WHERE slug LIKE 'qa-walkthrough-%';

SELECT 'QA accounts remaining: ' || count(*) FROM public.users WHERE email LIKE '%@local.test';

COMMIT;
