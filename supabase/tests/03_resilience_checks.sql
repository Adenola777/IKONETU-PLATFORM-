-- Checks for migration 20261015000004 (resilience). Each check prints PASS or
-- FAIL with what it found. Run it after the migrations, as a superuser, on its
-- own or after 01 and 02. It makes its own people:
--   X  a1a1a1a1-...  founder of Sample Ledger
--   Y  b2b2b2b2-...  an approved investor
--   Z  c3c3c3c3-...  a reviewer
-- The limit of ten requests a day under simultaneous requests needs two
-- sessions, so race_introductions.sh checks it separately.
\set ON_ERROR_STOP 1
reset role;

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

insert into auth.users values
  ('a1a1a1a1-0000-0000-0000-000000000001'), ('b2b2b2b2-0000-0000-0000-000000000002'), ('c3c3c3c3-0000-0000-0000-000000000003');
insert into public.profiles (user_id, full_name, role, status) values
  ('b2b2b2b2-0000-0000-0000-000000000002', 'Yemi Investor', 'investor', 'active'),
  ('c3c3c3c3-0000-0000-0000-000000000003', 'Zara Reviewer', 'reviewer', 'active');
insert into public.investor_profiles (user_id, investor_type, based_in, sectors, cheque_size, confirmed_statement)
values ('b2b2b2b2-0000-0000-0000-000000000002', 'angel', 'NG', array['Fintech'], 'Prefer not to say', true);

set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = 'a1a1a1a1-0000-0000-0000-000000000001';
insert into public.profiles (user_id, full_name, country) values (auth.uid(), 'Xola Founder', 'NG');
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('d4d4d4d4-0000-0000-0000-000000000001', auth.uid(), 'Sample Ledger', 'Fintech', 'NG', 'revenue');
insert into storage.objects (bucket_id, name) values
  ('evidence', 'a1a1a1a1-0000-0000-0000-000000000001/r1'),
  ('evidence', 'a1a1a1a1-0000-0000-0000-000000000001/r2'),
  ('pitches', 'a1a1a1a1-0000-0000-0000-000000000001/p.mp4');

-- R1 to R3: evidence and its files in one transaction, once per request key.
select public.submit_evidence('d4d4d4d4-0000-0000-0000-000000000001', 'revenue', 'Twelve months of bank statements', null,
  'e5e5e5e5-0000-0000-0000-000000000001',
  '[{"storage_path":"a1a1a1a1-0000-0000-0000-000000000001/r1","sha256":"x","mime_type":"application/pdf","size_bytes":100}]'::jsonb);
select pg_temp.ok('R1 submit_evidence saves the evidence and its file together',
  (select count(*) from public.evidence_files f join public.evidence e on e.id = f.evidence_id
   where e.request_key = 'e5e5e5e5-0000-0000-0000-000000000001') = 1);

do $$ begin
  perform public.submit_evidence('d4d4d4d4-0000-0000-0000-000000000001', 'tax_registration', 'A tax identification certificate', null,
    'e5e5e5e5-0000-0000-0000-000000000002',
    '[{"storage_path":"a1a1a1a1-0000-0000-0000-000000000001/r2","sha256":"x","mime_type":"text/html","size_bytes":100}]'::jsonb);
  perform pg_temp.ok('R2 a file that fails its check leaves no evidence behind', false, 'call succeeded');
exception when others then
  perform pg_temp.ok('R2 a file that fails its check leaves no evidence behind',
    not exists (select 1 from public.evidence where request_key = 'e5e5e5e5-0000-0000-0000-000000000002'), sqlerrm);
end $$;

do $$ begin
  perform public.submit_evidence('d4d4d4d4-0000-0000-0000-000000000001', 'revenue', 'Twelve months of bank statements', null,
    'e5e5e5e5-0000-0000-0000-000000000001', '[]'::jsonb);
  perform pg_temp.ok('R3 the same request key cannot add the evidence twice', false, 'second call succeeded');
exception when unique_violation then
  perform pg_temp.ok('R3 the same request key cannot add the evidence twice',
    (select count(*) from public.evidence where request_key = 'e5e5e5e5-0000-0000-0000-000000000001') = 1, sqlerrm);
end $$;

-- R3a and R3b: a founder may remove an unrecorded file of their own, never a recorded one.
insert into storage.objects (bucket_id, name) values ('evidence', 'a1a1a1a1-0000-0000-0000-000000000001/orphan');
delete from storage.objects where bucket_id = 'evidence' and name = 'a1a1a1a1-0000-0000-0000-000000000001/orphan';
reset role;
select pg_temp.ok('R3a a founder removes an unrecorded file of their own',
  not exists (select 1 from storage.objects where name = 'a1a1a1a1-0000-0000-0000-000000000001/orphan'));
set role authenticated;
set request.jwt.claim.sub = 'a1a1a1a1-0000-0000-0000-000000000001';
delete from storage.objects where bucket_id = 'evidence' and name = 'a1a1a1a1-0000-0000-0000-000000000001/r1';
reset role;
select pg_temp.ok('R3b a founder cannot remove a file their evidence records',
  exists (select 1 from storage.objects where name = 'a1a1a1a1-0000-0000-0000-000000000001/r1'));
set role authenticated;
set request.jwt.claim.sub = 'a1a1a1a1-0000-0000-0000-000000000001';

-- R4: founders no longer post progress updates (20261027000001), so the
-- request key on the update form has nothing left to guard.
do $$ begin
  insert into public.venture_updates (venture_id, body, request_key)
  values ('d4d4d4d4-0000-0000-0000-000000000001', 'We opened a second office this week.', 'e5e5e5e5-0000-0000-0000-000000000004');
  perform pg_temp.ok('R4 a founder can no longer post a progress update', false, 'insert succeeded');
exception when others then perform pg_temp.ok('R4 a founder can no longer post a progress update', sqlstate = '42501', sqlerrm);
end $$;

-- Publish the venture, so the investor can ask for an introduction.
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
values ('d4d4d4d4-0000-0000-0000-000000000001', 'a1a1a1a1-0000-0000-0000-000000000001/p.mp4', 'video/mp4', 1000, 58, 'Sample Ledger keeps the books of market traders.');
update public.ventures set published_at = now() where id = 'd4d4d4d4-0000-0000-0000-000000000001';

set request.jwt.claim.sub = 'b2b2b2b2-0000-0000-0000-000000000002';
insert into public.introductions (venture_id, note) values ('d4d4d4d4-0000-0000-0000-000000000001', 'I back payments companies in Lagos.');
set request.jwt.claim.sub = 'a1a1a1a1-0000-0000-0000-000000000001';
update public.introductions set status = 'accepted' where venture_id = 'd4d4d4d4-0000-0000-0000-000000000001';
insert into public.introduction_messages (introduction_id, sender_id, body, request_key)
select id, auth.uid(), 'Thank you. When suits you?', 'e5e5e5e5-0000-0000-0000-000000000005'
from public.introductions where venture_id = 'd4d4d4d4-0000-0000-0000-000000000001';
do $$ begin
  insert into public.introduction_messages (introduction_id, sender_id, body, request_key)
  select id, auth.uid(), 'Thank you. When suits you?', 'e5e5e5e5-0000-0000-0000-000000000005'
  from public.introductions where venture_id = 'd4d4d4d4-0000-0000-0000-000000000001';
  perform pg_temp.ok('R5 a message sent twice with one key is kept once', false, 'second insert succeeded');
exception when unique_violation then perform pg_temp.ok('R5 a message sent twice with one key is kept once', true);
end $$;

-- R6 and R7: who may call the new functions.
reset role;
set role anon;
set request.jwt.claim.role = 'anon';
reset request.jwt.claim.sub;
select pg_temp.ok('R6 a visitor who is not signed in can call health()', public.health());
do $$ begin
  perform public.submit_evidence('d4d4d4d4-0000-0000-0000-000000000001', 'revenue', 'Twelve months of bank statements', null, null, '[]'::jsonb);
  perform pg_temp.ok('R7 a visitor cannot call submit_evidence()', false, 'call succeeded');
exception when others then perform pg_temp.ok('R7 a visitor cannot call submit_evidence()', sqlstate = '42501', sqlerrm);
end $$;

-- R8 to R10: a decision whose score update failed shows up until the score is recorded.
reset role;
set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = 'c3c3c3c3-0000-0000-0000-000000000003';
select public.decide_evidence(p_evidence => (select id from public.evidence where request_key = 'e5e5e5e5-0000-0000-0000-000000000001'),
  p_decision => 'approve', p_lane => 'human', p_public_note => 'Compared with the bank statements.');
select pg_temp.ok('R8 a decision without a recorded score is listed as stale',
  exists (select 1 from public.ventures_with_stale_scores() where venture_id = 'd4d4d4d4-0000-0000-0000-000000000001'));
select public.record_score('d4d4d4d4-0000-0000-0000-000000000001', 80, 'EARLY', '[]'::jsonb, 'v2');
select pg_temp.ok('R9 recording the score takes it off the list',
  not exists (select 1 from public.ventures_with_stale_scores() where venture_id = 'd4d4d4d4-0000-0000-0000-000000000001'));
set request.jwt.claim.sub = 'a1a1a1a1-0000-0000-0000-000000000001';
do $$ begin
  perform * from public.ventures_with_stale_scores();
  perform pg_temp.ok('R10 a founder cannot list stale scores', false, 'call succeeded');
exception when others then perform pg_temp.ok('R10 a founder cannot list stale scores', sqlstate = '42501', sqlerrm);
end $$;

-- R11: the daily limit still refuses an eleventh request made on its own.
reset role;
do $$
declare i int; u uuid; v uuid;
begin
  for i in 1..10 loop
    u := gen_random_uuid(); v := gen_random_uuid();
    insert into auth.users (id) values (u);
    insert into public.profiles (user_id, role, status, full_name, country) values (u, 'founder', 'active', 'Limit Founder ' || i, 'NG');
    insert into public.ventures (id, founder_id, name, sector, stage, country) values (v, u, 'Limit Venture ' || i, 'Fintech', 'idea', 'NG');
    insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
    values (v, u || '/p.mp4', 'video/mp4', 1, 10, 'A transcript long enough for the check.');
    update public.ventures set published_at = now() where id = v;
  end loop;
end $$;
set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = 'b2b2b2b2-0000-0000-0000-000000000002';
insert into public.introductions (venture_id, note)
select id, 'A note of at least twenty characters.' from public.ventures where name in
  ('Limit Venture 1', 'Limit Venture 2', 'Limit Venture 3', 'Limit Venture 4', 'Limit Venture 5',
   'Limit Venture 6', 'Limit Venture 7', 'Limit Venture 8', 'Limit Venture 9');
do $$ begin
  insert into public.introductions (venture_id, note)
  select id, 'A note of at least twenty characters.' from public.ventures where name = 'Limit Venture 10';
  perform pg_temp.ok('R11 an eleventh request on the same day is refused', false, 'insert succeeded');
exception when others then perform pg_temp.ok('R11 an eleventh request on the same day is refused', sqlerrm like '%limit of 10 requests a day%', sqlerrm);
end $$;
reset role;
