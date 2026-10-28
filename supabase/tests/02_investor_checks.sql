-- Checks for the investor side (migration 20261015000002). Each check prints
-- PASS or FAIL with what it found. Run it after 00_supabase_stubs.sql, the
-- migrations and 01_rls_checks.sql, as a superuser. It makes its own people:
--   F  77777777-...  founder of Kola Pay
--   G  88888888-...  a second founder
--   I  33333333-...  an investor, approved during the checks
--   P  44444444-...  an investor who stays pending
--   A  55555555-...  an admin
--   R  66666666-...  a reviewer
\set ON_ERROR_STOP 1
reset role;
insert into auth.users values
  ('77777777-7777-7777-7777-777777777777'), ('88888888-8888-8888-8888-888888888888'),
  ('33333333-3333-3333-3333-333333333333'), ('44444444-4444-4444-4444-444444444444'),
  ('55555555-5555-5555-5555-555555555555'), ('66666666-6666-6666-6666-666666666666');
insert into public.profiles (user_id, full_name, role, status) values
  ('55555555-5555-5555-5555-555555555555', 'Ada Admin', 'admin', 'active'),
  ('66666666-6666-6666-6666-666666666666', 'Rex Reviewer', 'reviewer', 'active');

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- Founder F signs up, adds a venture and evidence.
set request.jwt.claim.sub = '77777777-7777-7777-7777-777777777777';
insert into public.profiles (user_id, full_name, city, country) values (auth.uid(), 'Kemi Bello', 'Lagos', 'NG');
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('bbbbbbbb-0000-0000-0000-000000000001', auth.uid(), 'Kola Pay', 'Fintech', 'NG', 'revenue');
insert into public.evidence (id, venture_id, signal_code, summary) values
  ('cccccccc-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001', 'revenue', 'Twelve months of bank statements');
-- Founders no longer post progress updates (20261027000001). An update posted
-- before that is written here directly, so the rules for reading one stay checked.
do $$ begin
  insert into public.venture_updates (venture_id, body) values ('bbbbbbbb-0000-0000-0000-000000000001', 'We signed our third market association this week.');
  perform pg_temp.ok('I0 a founder can no longer post a progress update', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I0 a founder can no longer post a progress update', sqlstate = '42501', sqlerrm);
end $$;
reset role;
insert into public.venture_updates (venture_id, body) values ('bbbbbbbb-0000-0000-0000-000000000001', 'We signed our third market association this week.');
set role authenticated;

do $$ begin
  insert into public.evidence (venture_id, signal_code, public_note) values ('bbbbbbbb-0000-0000-0000-000000000001', 'website_live', 'Checked by IkonetU');
  perform pg_temp.ok('I1 a founder cannot write the public review note', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I1 a founder cannot write the public review note', sqlstate = '42501', sqlerrm);
end $$;

do $$ begin
  insert into storage.objects (bucket_id, name) values ('evidence', '77777777-7777-7777-7777-777777777777/e1');
  insert into public.evidence_files (evidence_id, storage_path, sha256, mime_type, size_bytes)
  values ('cccccccc-0000-0000-0000-000000000001', '77777777-7777-7777-7777-777777777777/e1', 'x', 'application/pdf', 100);
  perform pg_temp.ok('I2 a founder records a file of their own evidence', true);
exception when others then perform pg_temp.ok('I2 a founder records a file of their own evidence', false, sqlerrm);
end $$;

do $$ begin
  insert into public.evidence_files (evidence_id, storage_path, sha256, mime_type, size_bytes)
  values ('cccccccc-0000-0000-0000-000000000001', '88888888-8888-8888-8888-888888888888/e2', 'x', 'application/pdf', 100);
  perform pg_temp.ok('I3 a founder cannot record a file in another folder', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I3 a founder cannot record a file in another folder', sqlstate = '42501', sqlerrm);
end $$;

do $$ begin
  update public.ventures set published_at = now() where id = 'bbbbbbbb-0000-0000-0000-000000000001';
  perform pg_temp.ok('I4 a venture without a pitch cannot be published', false, 'update succeeded');
exception when others then perform pg_temp.ok('I4 a venture without a pitch cannot be published', sqlerrm = 'add a pitch before publishing', sqlerrm);
end $$;

do $$ begin
  insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
  values ('bbbbbbbb-0000-0000-0000-000000000001', '88888888-8888-8888-8888-888888888888/p.mp4', 'video/mp4', 1000, 58, 'Kola Pay lets market traders take card payments.');
  perform pg_temp.ok('I5 a pitch cannot point into another founder''s folder', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I5 a pitch cannot point into another founder''s folder', sqlstate = '42501', sqlerrm);
end $$;

insert into storage.objects (bucket_id, name) values ('pitches', '77777777-7777-7777-7777-777777777777/p.mp4');
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
values ('bbbbbbbb-0000-0000-0000-000000000001', '77777777-7777-7777-7777-777777777777/p.mp4', 'video/mp4', 1000, 58,
        'Kola Pay lets market traders take card payments. We started in Lagos.');
update public.ventures set published_at = now() where id = 'bbbbbbbb-0000-0000-0000-000000000001';
select pg_temp.ok('I6 a venture with a pitch is published', published_at is not null) from public.ventures where id = 'bbbbbbbb-0000-0000-0000-000000000001';
do $$ begin
  update public.ventures set ask = 'Yes' where id = 'bbbbbbbb-0000-0000-0000-000000000001';
  perform pg_temp.ok('I6a an ask of fewer than 5 characters is refused', false, 'update succeeded');
exception when others then perform pg_temp.ok('I6a an ask of fewer than 5 characters is refused', sqlstate = '23514', sqlerrm);
end $$;
update public.ventures set ask = '$150,000 to reach 5,000 paying merchants' where id = 'bbbbbbbb-0000-0000-0000-000000000001';

-- Founder G sees nothing of F.
set request.jwt.claim.sub = '88888888-8888-8888-8888-888888888888';
insert into public.profiles (user_id, full_name) values (auth.uid(), 'Tunde Ade');
select pg_temp.ok('I7 another founder cannot read a published venture', count(*) = 0, count(*)::text) from public.ventures where id = 'bbbbbbbb-0000-0000-0000-000000000001';
select pg_temp.ok('I8 another founder cannot read the founder card', count(*) = 0, count(*)::text) from public.public_profiles where user_id <> auth.uid();
select pg_temp.ok('I9 another founder cannot read the pitch', count(*) = 0, count(*)::text) from public.pitches;
select pg_temp.ok('I10 another founder cannot read progress updates', count(*) = 0, count(*)::text) from public.venture_updates;
select pg_temp.ok('I11 another founder gets no evidence from venture_evidence', count(*) = 0, count(*)::text) from public.venture_evidence('bbbbbbbb-0000-0000-0000-000000000001');
select pg_temp.ok('I12 another founder gets nothing from discovery', count(*) = 0, count(*)::text) from public.discover_ventures();

-- Investor P signs up and stays pending.
set request.jwt.claim.sub = '44444444-4444-4444-4444-444444444444';
do $$ begin
  insert into public.profiles (user_id, full_name, role, status) values (auth.uid(), 'Pat Pending', 'investor', 'active');
  perform pg_temp.ok('I13 an investor cannot sign up as already approved', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I13 an investor cannot sign up as already approved', sqlstate = '42501', sqlerrm);
end $$;
insert into public.profiles (user_id, full_name, role, status) values (auth.uid(), 'Pat Pending', 'investor', 'pending');
insert into public.investor_profiles (user_id, investor_type, based_in, sectors, cheque_size, confirmed_statement)
values (auth.uid(), 'angel', 'other', array['Fintech'], 'Prefer not to say', true);
select pg_temp.ok('I14 a pending investor reads their own investor profile', count(*) = 1, count(*)::text) from public.investor_profiles;
select pg_temp.ok('I15 a pending investor cannot read published ventures', count(*) = 0, count(*)::text) from public.ventures;
select pg_temp.ok('I16 a pending investor gets nothing from discovery', count(*) = 0, count(*)::text) from public.discover_ventures();
do $$ begin
  update public.profiles set status = 'active' where user_id = auth.uid();
  perform pg_temp.ok('I17 a pending investor cannot approve themselves', false, 'update succeeded');
exception when others then perform pg_temp.ok('I17 a pending investor cannot approve themselves', sqlerrm like 'role and status%', sqlerrm);
end $$;
do $$ begin
  insert into public.introductions (venture_id, note) values ('bbbbbbbb-0000-0000-0000-000000000001', 'I would like to talk about your payments product.');
  perform pg_temp.ok('I18 a pending investor cannot request an introduction', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I18 a pending investor cannot request an introduction', sqlstate = '42501', sqlerrm);
end $$;

-- Investor I signs up.
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
insert into public.profiles (user_id, full_name, role, status) values (auth.uid(), 'Ife Investor', 'investor', 'pending');
insert into public.investor_profiles (user_id, investor_type, firm, based_in, sectors, stages, countries, cheque_size, confirmed_statement)
values (auth.uid(), 'fund', 'Savannah Seed', 'NG', array['Fintech', 'Health'], array['revenue']::public.product_stage[], array['NG']::public.country_code[], '$25,000 to $100,000', true);
select pg_temp.ok('I19 an investor cannot read another investor''s profile', count(*) = 1, count(*)::text) from public.investor_profiles;
do $$ begin
  perform public.decide_investor('33333333-3333-3333-3333-333333333333', true);
  perform pg_temp.ok('I20 an investor cannot approve themselves through the function', false, 'call succeeded');
exception when others then perform pg_temp.ok('I20 an investor cannot approve themselves through the function', sqlstate = '42501', sqlerrm);
end $$;

-- The reviewer is not an admin, so cannot approve investors.
set request.jwt.claim.sub = '66666666-6666-6666-6666-666666666666';
do $$ begin
  perform public.decide_investor('33333333-3333-3333-3333-333333333333', true);
  perform pg_temp.ok('I21 a reviewer cannot approve investors', false, 'call succeeded');
exception when others then perform pg_temp.ok('I21 a reviewer cannot approve investors', sqlstate = '42501', sqlerrm);
end $$;

-- The admin sees pending investors and approves I.
set request.jwt.claim.sub = '55555555-5555-5555-5555-555555555555';
select pg_temp.ok('I22 an admin reads pending investors', count(*) = 2, count(*)::text) from public.profiles where role = 'investor' and status = 'pending';
select pg_temp.ok('I23 an admin reads investor profiles', count(*) = 2, count(*)::text) from public.investor_profiles;
select public.decide_investor('33333333-3333-3333-3333-333333333333', true);
select pg_temp.ok('I24 the approved investor is active', status = 'active', status::text) from public.profiles where user_id = '33333333-3333-3333-3333-333333333333';

-- Investor I, approved, discovers Kola Pay.
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
select pg_temp.ok('I25 an approved investor reads the published venture', count(*) = 1, count(*)::text) from public.ventures;
select pg_temp.ok('I26 discovery returns the venture with its evidence area', count(*) = 1 and bool_and(areas @> '[{"category": "financial", "status": "submitted"}]'), count(*)::text) from public.discover_ventures();
select pg_temp.ok('I26a discovery returns the founder''s ask', bool_and(ask = '$150,000 to reach 5,000 paying merchants'), coalesce(string_agg(ask, ','), 'none')) from public.discover_ventures();
select pg_temp.ok('I27 the sector filter narrows', count(*) = 0, count(*)::text) from public.discover_ventures(p_sectors => array['Health']);
select pg_temp.ok('I28 two sectors widen', count(*) = 1, count(*)::text) from public.discover_ventures(p_sectors => array['Health', 'Fintech']);
select pg_temp.ok('I29 the reviewed-revenue filter excludes unreviewed revenue', count(*) = 0, count(*)::text) from public.discover_ventures(p_evidence => array['revenue_reviewed']);
select pg_temp.ok('I30 the activity filter keeps a venture active today', count(*) = 1, count(*)::text) from public.discover_ventures(p_active_days => 30);
select pg_temp.ok('I31 an investor cannot read scores', count(*) = 0, count(*)::text) from public.scores;
select pg_temp.ok('I32 an investor cannot read the evidence table', count(*) = 0, count(*)::text) from public.evidence;
select pg_temp.ok('I33 an investor cannot read evidence files', count(*) = 0, count(*)::text) from public.evidence_files;
select pg_temp.ok('I34 venture_evidence shows the evidence as founder submitted', count(*) = 1 and bool_and(shown_status = 'submitted' and public_note is null), count(*)::text) from public.venture_evidence('bbbbbbbb-0000-0000-0000-000000000001');
select pg_temp.ok('I35 an investor reads the pitch row', count(*) = 1, count(*)::text) from public.pitches;
select pg_temp.ok('I36 an investor reads the pitch file', count(*) = 1, count(*)::text) from storage.objects where bucket_id = 'pitches';
select pg_temp.ok('I37 an investor cannot read evidence files in storage', count(*) = 0, count(*)::text) from storage.objects where bucket_id = 'evidence';
select pg_temp.ok('I38 an investor reads the founder card', count(*) = 1, count(*)::text) from public.public_profiles;
select pg_temp.ok('I39 an investor reads progress updates', count(*) = 1, count(*)::text) from public.venture_updates;
select pg_temp.ok('I40 an investor cannot read the founder''s profile row', count(*) = 0, count(*)::text) from public.profiles where user_id = '77777777-7777-7777-7777-777777777777';

-- Investor I requests an introduction, and tries to forge it.
insert into public.introductions (venture_id, founder_id, note, status, investor_name)
values ('bbbbbbbb-0000-0000-0000-000000000001', '88888888-8888-8888-8888-888888888888',
        'We back payments companies in Lagos and would like to hear more.', 'accepted', 'Someone Famous');
select pg_temp.ok('I41 the request is pending, addressed to the right founder, under the investor''s real name',
  status = 'pending' and founder_id = '77777777-7777-7777-7777-777777777777' and investor_name = 'Ife Investor'
  and investor_firm = 'Savannah Seed' and investor_type = 'fund' and venture_name = 'Kola Pay' and founder_name = 'Kemi Bello',
  status || ' ' || founder_id || ' ' || investor_name) from public.introductions;
do $$ begin
  insert into public.introductions (venture_id, note) values ('bbbbbbbb-0000-0000-0000-000000000001', 'Asking a second time about the same company.');
  perform pg_temp.ok('I42 a second open request to the same venture is refused', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I42 a second open request to the same venture is refused', sqlstate = '23505', sqlerrm);
end $$;
do $$ begin
  update public.introductions set status = 'accepted';
  perform pg_temp.ok('I43 an investor cannot accept their own request', false, 'update succeeded');
exception when others then perform pg_temp.ok('I43 an investor cannot accept their own request', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  insert into public.introduction_messages (introduction_id, sender_id, body)
  select id, auth.uid(), 'Hello before you have answered.' from public.introductions;
  perform pg_temp.ok('I44 no message before the founder accepts', false, 'insert succeeded');
exception when others then perform pg_temp.ok('I44 no message before the founder accepts', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.decide_evidence('cccccccc-0000-0000-0000-000000000001', 'approve', 'human', 'Compared with the bank statements');
  perform pg_temp.ok('I45 an investor cannot decide evidence', false, 'call succeeded');
exception when others then perform pg_temp.ok('I45 an investor cannot decide evidence', sqlstate = '42501', sqlerrm);
end $$;

-- Founder G cannot see the request.
set request.jwt.claim.sub = '88888888-8888-8888-8888-888888888888';
select pg_temp.ok('I46 another founder cannot read the request', count(*) = 0, count(*)::text) from public.introductions;

-- Founder F answers.
set request.jwt.claim.sub = '77777777-7777-7777-7777-777777777777';
select pg_temp.ok('I47 the founder reads the request', count(*) = 1, count(*)::text) from public.introductions;
do $$ begin
  update public.introductions set note = 'Changed note to look better.';
  perform pg_temp.ok('I48 the founder cannot change the note', false, 'update succeeded');
exception when others then perform pg_temp.ok('I48 the founder cannot change the note', sqlstate = '42501', sqlerrm);
end $$;
update public.introductions set status = 'accepted';
select pg_temp.ok('I49 the founder accepts, and the answer is dated', status = 'accepted' and decided_at is not null, status::text) from public.introductions;
do $$ begin
  update public.introductions set status = 'declined';
  perform pg_temp.ok('I50 an answered request cannot be answered again', false, 'update succeeded');
exception when others then perform pg_temp.ok('I50 an answered request cannot be answered again', sqlerrm = 'this request has already been answered', sqlerrm);
end $$;
insert into public.introduction_messages (introduction_id, sender_id, body)
select id, auth.uid(), 'Thank you. Happy to talk next week.' from public.introductions;
do $$ declare n integer; begin
  update public.introduction_messages set body = 'Edited';
  get diagnostics n = row_count;
  perform pg_temp.ok('I51 a message cannot be edited', n = 0, n::text || ' rows changed');
exception when others then perform pg_temp.ok('I51 a message cannot be edited', sqlerrm like '%append-only%', sqlerrm);
end $$;
do $$ begin
  perform public.record_score('bbbbbbbb-0000-0000-0000-000000000001', 1000, 'ELITE', '[]'::jsonb, 'v2');
  perform pg_temp.ok('I52 a founder cannot record their own score', false, 'call succeeded');
exception when others then perform pg_temp.ok('I52 a founder cannot record their own score', sqlstate = '42501', sqlerrm);
end $$;

-- Investor I replies.
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
insert into public.introduction_messages (introduction_id, sender_id, body)
select id, auth.uid(), 'Tuesday at ten works for us.' from public.introductions;
select pg_temp.ok('I53 the investor reads both messages', count(*) = 2, count(*)::text) from public.introduction_messages;

-- Founder G cannot read the conversation.
set request.jwt.claim.sub = '88888888-8888-8888-8888-888888888888';
select pg_temp.ok('I54 another founder cannot read the conversation', count(*) = 0, count(*)::text) from public.introduction_messages;

-- The reviewer approves the revenue evidence.
set request.jwt.claim.sub = '66666666-6666-6666-6666-666666666666';
select pg_temp.ok('I55 a reviewer reads submitted evidence', count(*) >= 1, count(*)::text) from public.evidence where status = 'submitted';
select pg_temp.ok('I56 a reviewer can open evidence files in storage', count(*) >= 1, count(*)::text) from storage.objects where bucket_id = 'evidence';
do $$ begin
  perform public.decide_evidence('cccccccc-0000-0000-0000-000000000001', 'approve', 'human', '');
  perform pg_temp.ok('I57 an approval needs a note of what was compared', false, 'call succeeded');
exception when others then perform pg_temp.ok('I57 an approval needs a note of what was compared', sqlerrm = 'say what was compared', sqlerrm);
end $$;
select public.decide_evidence('cccccccc-0000-0000-0000-000000000001', 'approve', 'human',
  'Compared the stated revenue with twelve months of bank statements', p_revenue_usd => 18000);
select public.record_score('bbbbbbbb-0000-0000-0000-000000000001', 72, 'EARLY', '[]'::jsonb, 'v2', 'cccccccc-0000-0000-0000-000000000001');
do $$ begin
  perform public.decide_evidence('cccccccc-0000-0000-0000-000000000001', 'reject', null, null, 'Changing my mind later');
  perform pg_temp.ok('I58 a decided item cannot be decided again', false, 'call succeeded');
exception when others then perform pg_temp.ok('I58 a decided item cannot be decided again', sqlerrm = 'this evidence has already been decided', sqlerrm);
end $$;

-- Investor I sees the review.
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
select pg_temp.ok('I59 the investor sees the evidence as platform reviewed, with the note and date',
  count(*) = 1 and bool_and(shown_status = 'reviewed' and public_note like 'Compared%' and reviewed_at is not null), count(*)::text)
from public.venture_evidence('bbbbbbbb-0000-0000-0000-000000000001');
select pg_temp.ok('I60 the reviewed-revenue filter now finds the venture', count(*) = 1, count(*)::text) from public.discover_ventures(p_evidence => array['revenue_reviewed']);
select pg_temp.ok('I61 the registry filter does not', count(*) = 0, count(*)::text) from public.discover_ventures(p_evidence => array['registry_record']);

-- The founder reads the score history; the audit log holds the decisions.
set request.jwt.claim.sub = '77777777-7777-7777-7777-777777777777';
select pg_temp.ok('I62 the founder reads their recorded score', count(*) = 1 and bool_and(total = 72), count(*)::text) from public.scores;
reset role;
select pg_temp.ok('I63 the audit log holds the investor approval and the evidence decision',
  count(*) filter (where action = 'investor.approve') = 1 and count(*) filter (where action = 'evidence.approve') = 1, count(*)::text)
from public.audit_log;
select pg_temp.ok('I64 the review is recorded', count(*) = 1, count(*)::text) from public.reviews where evidence_id = 'cccccccc-0000-0000-0000-000000000001';
set role authenticated;

-- A rejected item is hidden from investors.
set request.jwt.claim.sub = '77777777-7777-7777-7777-777777777777';
insert into public.evidence (id, venture_id, signal_code, summary) values
  ('cccccccc-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000001', 'press_coverage', 'An article in a newspaper');
set request.jwt.claim.sub = '66666666-6666-6666-6666-666666666666';
select public.decide_evidence('cccccccc-0000-0000-0000-000000000002', 'reject', null, null, 'The article does not mention Kola Pay.');
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
select pg_temp.ok('I65 rejected evidence is hidden from investors', count(*) = 1, count(*)::text) from public.venture_evidence('bbbbbbbb-0000-0000-0000-000000000001');

-- The founder hides the profile again.
set request.jwt.claim.sub = '77777777-7777-7777-7777-777777777777';
update public.ventures set published_at = null where id = 'bbbbbbbb-0000-0000-0000-000000000001';
set request.jwt.claim.sub = '33333333-3333-3333-3333-333333333333';
select pg_temp.ok('I66 a hidden venture leaves discovery', count(*) = 0, count(*)::text) from public.discover_ventures();
select pg_temp.ok('I67 a hidden venture cannot be read', count(*) = 0, count(*)::text) from public.ventures;
select pg_temp.ok('I68 its pitch file cannot be read', count(*) = 0, count(*)::text) from storage.objects where bucket_id = 'pitches';
select pg_temp.ok('I69 its evidence cannot be read', count(*) = 0, count(*)::text) from public.venture_evidence('bbbbbbbb-0000-0000-0000-000000000001');
select pg_temp.ok('I70 its founder card cannot be read', count(*) = 0, count(*)::text) from public.public_profiles;
select pg_temp.ok('I71 the existing conversation stays readable to the two people involved', count(*) = 2, count(*)::text) from public.introduction_messages;

-- The admin declines investor P.
set request.jwt.claim.sub = '55555555-5555-5555-5555-555555555555';
select public.decide_investor('44444444-4444-4444-4444-444444444444', false);
set request.jwt.claim.sub = '44444444-4444-4444-4444-444444444444';
select pg_temp.ok('I72 a declined investor is suspended and can read no venture', count(*) = 0, count(*)::text) from public.ventures;

-- Visitors who are not signed in.
reset role;
set role anon;
reset request.jwt.claim.sub;
set request.jwt.claim.role = 'anon';
do $$ begin
  perform count(*) from public.discover_ventures();
  perform pg_temp.ok('I73 a visitor cannot call discovery', false, 'call succeeded');
exception when others then perform pg_temp.ok('I73 a visitor cannot call discovery', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform count(*) from public.introductions;
  perform pg_temp.ok('I74 a visitor cannot read introductions', false, 'read succeeded');
exception when others then perform pg_temp.ok('I74 a visitor cannot read introductions', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform count(*) from public.pitches;
  perform pg_temp.ok('I75 a visitor cannot read pitches', false, 'read succeeded');
exception when others then perform pg_temp.ok('I75 a visitor cannot read pitches', sqlstate = '42501', sqlerrm);
end $$;
reset role;
