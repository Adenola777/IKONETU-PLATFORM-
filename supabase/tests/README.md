# Database access tests

These scripts check the row level security rules in `supabase/migrations` on a plain Postgres 16 server.

1. `00_supabase_stubs.sql` creates the small parts of Supabase that the migrations expect: the `auth` schema with `auth.uid()`, the `anon` and `authenticated` roles, and the `storage` schema. It also sets the default privileges a real Supabase project has, which give `anon` and `authenticated` every right on each new table, view and function in `public`.
2. Apply the migration files in order.
3. `01_rls_checks.sql` runs 23 checks, as signed-in users and as a visitor who is not signed in. Each check prints what it expects, for example "expect RLS error" or "expect 0 rows".

Example:

```sh
createdb ikonetu_test
psql -d ikonetu_test -f supabase/tests/00_supabase_stubs.sql
psql -d ikonetu_test -f supabase/migrations/20261005000001_core.sql
psql -d ikonetu_test -f supabase/migrations/20261005000002_rubric_v2.sql
psql -d ikonetu_test -f supabase/migrations/20261005000003_lock_public_profiles.sql
psql -d ikonetu_test -f supabase/tests/01_rls_checks.sql
```

All 23 checks gave the expected result on 5 October 2026. Checks 16 to 23 were added the same day, after Supabase's advisor found that `public_profiles` could be read, changed and emptied by a visitor who is not signed in; without migration 0003, checks 16, 17, 18 and 19 fail. Run them again after any change to a policy.
