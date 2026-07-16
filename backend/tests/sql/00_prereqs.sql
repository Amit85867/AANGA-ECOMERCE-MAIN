-- Prerequisites that Supabase provides out of the box but a plain Postgres
-- (our Docker test database) does not. Loaded before schema.sql so the
-- canonical dump applies without modification.
--
--  * extensions.uuid_generate_v4()  -> uuid-ossp, used as a column default
--  * auth.uid()                      -> Supabase RLS helper referenced by the
--                                       CREATE POLICY statements. The Flask app
--                                       connects as the table owner and bypasses
--                                       RLS, so a stub returning NULL is enough
--                                       to let the policies be created.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE AS $$ SELECT NULL::uuid $$;
