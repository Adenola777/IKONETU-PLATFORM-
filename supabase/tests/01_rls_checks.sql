\set ON_ERROR_STOP 0
grant usage on schema public, auth, storage to anon, authenticated;
grant all on all tables in schema public to anon, authenticated;
grant all on all sequences in schema public to anon, authenticated;
grant all on storage.objects to authenticated;
grant execute on all functions in schema public, auth, storage to anon, authenticated;
insert into auth.users values ('11111111-1111-1111-1111-111111111111'), ('22222222-2222-2222-2222-222222222222');
insert into public.rubric_versions (version, is_active) values ('v2', true) on conflict do nothing;

set role authenticated;
set request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
set request.jwt.claim.role = 'authenticated';
\echo T1 create own founder profile (expect ok)
insert into public.profiles (user_id, full_name) values ('11111111-1111-1111-1111-111111111111', 'Amara Okafor');
\echo T2 create profile as admin (expect RLS error)
insert into public.profiles (user_id, full_name, role) values ('11111111-1111-1111-1111-111111111111', 'X', 'admin');
\echo T3 promote self to admin (expect guard error)
update public.profiles set role = 'admin' where user_id = auth.uid();
\echo T4 create venture (expect ok)
insert into public.ventures (id, founder_id, name, sector, country) values ('aaaaaaaa-0000-0000-0000-000000000001', auth.uid(), 'LearnLoop', 'Edtech', 'NG');
\echo T5 submit evidence pre-approved (expect RLS error)
insert into public.evidence (venture_id, signal_code, status, lane) values ('aaaaaaaa-0000-0000-0000-000000000001', 'tax_registration', 'approved', 'government');
\echo T6 submit evidence correctly (expect ok)
insert into public.evidence (venture_id, signal_code) values ('aaaaaaaa-0000-0000-0000-000000000001', 'tax_registration');
\echo T7 founder edits own evidence status (expect 0 rows updated)
update public.evidence set status = 'approved';
\echo T8 waitlist read as signed-in user (expect 0 rows)
select count(*) as waitlist_rows from public.waitlist;
\echo T9 upload into own folder (expect ok)
insert into storage.objects (bucket_id, name) values ('evidence', '11111111-1111-1111-1111-111111111111/abc.pdf');
\echo T10 upload into another user folder (expect RLS error)
insert into storage.objects (bucket_id, name) values ('evidence', '22222222-2222-2222-2222-222222222222/abc.pdf');

set request.jwt.claim.sub = '22222222-2222-2222-2222-222222222222';
\echo T11 second user reads first user evidence (expect 0)
select count(*) as visible_evidence from public.evidence;
\echo T12 second user can see the venture card (expect 1)
select count(*) as visible_ventures from public.ventures;
\echo T13 second user submits evidence on first user venture (expect RLS error)
insert into public.evidence (venture_id, signal_code) values ('aaaaaaaa-0000-0000-0000-000000000001', 'website_live');

reset role;
insert into public.score_events (venture_id, total, league, delta) values ('aaaaaaaa-0000-0000-0000-000000000001', 42, 'EARLY', 42);
\echo T14 update score history (expect append-only error)
update public.score_events set total = 999;
\echo T15 evidence state after tests
select signal_code, status, lane from public.evidence;
