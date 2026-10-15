#!/bin/sh
# Checks the limit of ten introduction requests a day under simultaneous
# requests, which one SQL session cannot do. An investor with nine requests
# sends two more at the same moment from two sessions. Before migration
# 20261015000004 both passed and made eleven. With it, one waits for the other
# and is refused, so ten remain.
#
# Usage, as a superuser, on a database with the stubs and every migration:
#   sh supabase/tests/race_introductions.sh <psql connection options>
# for example: sh supabase/tests/race_introductions.sh -d ikonetu_test
set -e
P="psql -X -q -v ON_ERROR_STOP=1 $*"
INVESTOR=f6f6f6f6-0000-0000-0000-000000000006

$P <<SQL
reset role;
insert into auth.users (id) values ('$INVESTOR');
insert into public.profiles (user_id, role, status, full_name, country) values ('$INVESTOR', 'investor', 'active', 'Race Investor', 'NG');
insert into public.investor_profiles (user_id, investor_type, based_in, sectors, cheque_size, confirmed_statement)
values ('$INVESTOR', 'angel', 'NG', array['Fintech'], 'Prefer not to say', true);
do \$\$
declare i int; u uuid; v uuid;
begin
  for i in 1..11 loop
    u := gen_random_uuid(); v := gen_random_uuid();
    insert into auth.users (id) values (u);
    insert into public.profiles (user_id, role, status, full_name, country) values (u, 'founder', 'active', 'Race Founder ' || i, 'NG');
    insert into public.ventures (id, founder_id, name, sector, stage, country) values (v, u, 'Race Venture ' || i, 'Fintech', 'idea', 'NG');
    insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
    values (v, u || '/p.mp4', 'video/mp4', 1, 10, 'A transcript long enough for the check.');
    update public.ventures set published_at = now() where id = v;
  end loop;
end \$\$;
set role authenticated;
set request.jwt.claim.sub = '$INVESTOR';
insert into public.introductions (venture_id, note)
select id, 'A note of at least twenty characters.' from public.ventures where name in
  ('Race Venture 1', 'Race Venture 2', 'Race Venture 3', 'Race Venture 4', 'Race Venture 5',
   'Race Venture 6', 'Race Venture 7', 'Race Venture 8', 'Race Venture 9');
SQL

one() {
  $P <<SQL
begin;
set local role authenticated;
select set_config('request.jwt.claim.sub', '$INVESTOR', true);
insert into public.introductions (venture_id, note)
select id, 'A note of at least twenty characters.' from public.ventures where name = '$1';
select pg_sleep(2);
commit;
SQL
}
one 'Race Venture 10' > /dev/null 2>&1 &
one 'Race Venture 11' > /dev/null 2>&1 &
wait

COUNT=$($P -tA -c "select count(*) from public.introductions where investor_id = '$INVESTOR'")
if [ "$COUNT" = "10" ]; then echo "PASS T1 two simultaneous requests at nine leave ten"; else echo "FAIL T1 two simultaneous requests at nine left $COUNT"; fi
