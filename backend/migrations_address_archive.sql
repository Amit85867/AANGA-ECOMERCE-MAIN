-- Migration: archive addresses instead of deleting or rewriting them.
--
-- orders.address_id references addresses(id) ON DELETE RESTRICT and the order
-- reads its delivery address through that row. So an address an order points
-- at can be neither deleted (the FK refuses, which surfaced as a 500) nor
-- edited in place (that would rewrite where a past order was delivered).
--
-- archived_at hides such a row from the customer's address book while keeping
-- it for the orders that used it. Safe to run more than once.

ALTER TABLE public.addresses
    ADD COLUMN IF NOT EXISTS archived_at timestamp with time zone;

CREATE INDEX IF NOT EXISTS idx_addresses_user_active
    ON public.addresses USING btree (user_id)
    WHERE (archived_at IS NULL);
