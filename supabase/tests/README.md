# Database access tests

These scripts check the row level security rules in `supabase/migrations` on a plain Postgres 16 server.

1. `00_supabase_stubs.sql` creates the small parts of Supabase that the migrations expect: the `auth` schema with `auth.uid()` and `auth.role()` and an `auth.users` table with `email` and `last_sign_in_at`, which read the claims both ways Supabase's own functions do, the `anon` and `authenticated` roles, and the `storage` schema. It also sets the default privileges a real Supabase project has, which give `anon` and `authenticated` every right on each new table, view and function in `public`.
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
psql -d ikonetu_test -f supabase/migrations/20261015000004_resilience.sql
psql -d ikonetu_test -f supabase/migrations/20261017000001_admin.sql
psql -d ikonetu_test -f supabase/tests/01_rls_checks.sql
psql -d ikonetu_test -f supabase/tests/02_investor_checks.sql 2>&1 | grep -c FAIL   # 0 when every check passes
psql -d ikonetu_test -f supabase/tests/03_resilience_checks.sql 2>&1 | grep -c FAIL # 0 when every check passes
psql -d ikonetu_test -f supabase/tests/04_admin_checks.sql 2>&1 | grep -c FAIL      # 0 when every check passes
sh supabase/tests/race_introductions.sh -d ikonetu_test                            # prints PASS or FAIL
```

All 23 checks gave the expected result on 5 October 2026. Checks 16 to 23 were added the same day, after Supabase's advisor found that `public_profiles` could be read, changed and emptied by a visitor who is not signed in; without migration 0003, checks 16, 17, 18 and 19 fail. Run them again after any change to a policy.

Checks T8b and T8c were added on 15 October 2026 with the `investor_interest` table. They check that a signed-in user can neither read nor write it. All 25 checks gave the expected result that day on a local PostgreSQL 16, with the four migrations applied in order.

Migration 20261015000002 was added on 15 October 2026. With all five migrations applied on a local PostgreSQL 16 that day, the 25 checks in `01_rls_checks.sql` gave the expected result and the 75 checks in `02_investor_checks.sql` passed. Two checks in the first file changed with it: a second founder can no longer see another founder's venture (T12) or founder card (T20), because a venture is now visible only to approved investors, and only once its founder publishes it.

Migration 20261015000003 adds the founder's ask, and checks I6a and I26a cover it. With all six migrations applied on a local PostgreSQL 16 on 15 October 2026, the 77 checks in `02_investor_checks.sql` passed.

Migration 20261015000004 adds the checks in `03_resilience_checks.sql` and `race_introductions.sh`. The 13 checks cover evidence and its files saved in one transaction, a founder removing only an unrecorded file of their own, a form sent twice kept once, who may call `health()`, `submit_evidence()` and `ventures_with_stale_scores()`, and the daily limit on introduction requests. `race_introductions.sh` sends two requests at the same moment from two sessions. Without the migration they made eleven requests out of a limit of ten; with it they leave ten. All of it passed on a local PostgreSQL 16 on 15 October 2026, with the seven migrations applied in order, and the 77 checks in `02_investor_checks.sql` still passed.

Migration 20261017000001 adds the checks in `04_admin_checks.sql`. The 43 checks cover who may read the overview, the founders list and the accounts list; the north star count; hiding a profile with a reason, the founder reading it and being unable to publish or lift it, and lifting it; a venture created already published without a pitch; role changes, including that nobody changes their own role and that a founder made staff leaves investors' view; and suspension, including that a suspended founder cannot add evidence, publish, rename the venture, answer a request or send a message, and that a suspended admin loses access. All of it passed on a local PostgreSQL 16 on 17 October 2026 with the eight migrations applied in order. The 77 checks in `02_investor_checks.sql`, the 13 in `03_resilience_checks.sql` and the race check still passed, and the output of `01_rls_checks.sql` was the same as on 15 October. On a database without this migration, a founder created a venture already published without a pitch, and a suspended founder added evidence.
