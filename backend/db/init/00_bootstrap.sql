-- Runs first, once, on an empty data volume. See docker-compose.yml.
--
-- Two jobs, both about making a stock Postgres accept a dump taken from
-- Supabase without editing the dump itself.

-- 1. schema.sql opens with its own `CREATE SCHEMA public;`, which collides
--    with the one every new Postgres database ships with.
DROP SCHEMA IF EXISTS public CASCADE;

-- 2. Supabase grants table privileges to these built-in roles, and RLS
--    policies may name them. They do not exist on a plain server, so a
--    dump that references them fails to restore. Login is disabled: nothing
--    authenticates as these, they exist purely so GRANT/POLICY resolves.
--
--    The current schema.sql happens not to reference them (it was dumped with
--    --no-owner --no-acl), but a full dump taken by db/migrate-from-supabase.ps1
--    can, so create them up front.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
    END IF;
END
$$;
