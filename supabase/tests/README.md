# Database access tests

These scripts check the row level security rules in `supabase/migrations` on a plain Postgres 16 server.

1. `00_supabase_stubs.sql` creates the small parts of Supabase that the migrations expect: the `auth` schema with `auth.uid()` and `auth.role()`, which read the claims both ways Supabase's own functions do, the `anon` and `authenticated` roles, and the `storage` schema. It also sets the default privileges a real Supabase project has, which give `anon` and `authenticated` every right on each new table, view and function in `public`.
2. Apply the migration files in order.
3. `01_rls_checks.sql` runs 25 checks, as signed-in users and as a visitor who is not signed in. Each check prints what it expects, for example "expect RLS error" or "expect 0 rows".
4. `02_investor_checks.sql` runs 77 checks of the investor side: sign-up as a pending investor, an admin's approval, publishing, discovery, the evidence an investor may see, introductions, conversations, staff decisions and recorded scores. It makes its own people, and each check prints PASS or FAIL with what it found, so a run is read by counting the FAIL lines.

Example:

```sh
createdb ikonetu_test
psql -d ikonetu_test -f supabase/tests/00_supabase_stubs.sql
psql -d ikonetu_test -f supabase/migrations/20261005000001_core.sql
psql -d ikonetu_test -f supabase/migrations/20261005000002_rubric_v2.sql
psql -d ikonetu_test -f supabase/migrations/20261005000003_lock_public_profiles.sql
psql -d ikonetu_test -f supabase/migrations/20261015000001_investor_interest.sql
psql -d ikonetu_test -f supabase/migrations/20261015000002_investor_side.sql
psql -d ikonetu_test -f supabase/migrations/20261015000003_venture_ask.sql
psql -d ikonetu_test -f supabase/tests/01_rls_checks.sql
psql -d ikonetu_test -f supabase/tests/02_investor_checks.sql 2>&1 | grep -c FAIL   # 0 when every check passes
```

All 23 checks gave the expected result on 5 October 2026. Checks 16 to 23 were added the same day, after Supabase's advisor found that `public_profiles` could be read, changed and emptied by a visitor who is not signed in; without migration 0003, checks 16, 17, 18 and 19 fail. Run them again after any change to a policy.

Checks T8b and T8c were added on 15 October 2026 with the `investor_interest` table. They check that a signed-in user can neither read nor write it. All 25 checks gave the expected result that day on a local PostgreSQL 16, with the four migrations applied in order.

Migration 20261015000002 was added on 15 October 2026. With all five migrations applied on a local PostgreSQL 16 that day, the 25 checks in `01_rls_checks.sql` gave the expected result and the 75 checks in `02_investor_checks.sql` passed. Two checks in the first file changed with it: a second founder can no longer see another founder's venture (T12) or founder card (T20), because a venture is now visible only to approved investors, and only once its founder publishes it.

Migration 20261015000003 adds the founder's ask, and checks I6a and I26a cover it. With all six migrations applied on a local PostgreSQL 16 on 15 October 2026, the 77 checks in `02_investor_checks.sql` passed.
