# Database access tests

These scripts check the row level security rules in `supabase/migrations` on a plain Postgres 16 server.

1. `00_supabase_stubs.sql` creates the small parts of Supabase that the migrations expect: the `auth` schema with `auth.uid()`, the `anon` and `authenticated` roles, and the `storage` schema.
2. Apply both migration files in order.
3. `01_rls_checks.sql` runs 15 checks as signed-in users. Each check prints what it expects, for example "expect RLS error" or "expect 0 rows".

Example:

```sh
createdb ikonetu_test
psql -d ikonetu_test -f supabase/tests/00_supabase_stubs.sql
psql -d ikonetu_test -f supabase/migrations/20261005000001_core.sql
psql -d ikonetu_test -f supabase/migrations/20261005000002_rubric_v2.sql
psql -d ikonetu_test -f supabase/tests/01_rls_checks.sql
```

All 15 checks gave the expected result on 5 October 2026. Run them again after any change to a policy.
