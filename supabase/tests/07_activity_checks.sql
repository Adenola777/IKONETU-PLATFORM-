-- Checks for migration 20261027000001 (the activity feed). Each check prints
-- PASS or FAIL with what it found. Run it after the migrations, as a
-- superuser, on its own or after 01 to 06. It makes its own people and two
-- ventures, and reads only their entries, so other files' ventures do not count:
--   F  9e...0f  founder of Kola Farms     G  9e...10  founder of Duka Books
--   I  9e...12  an approved angel         J  9e...13  an approved fund
--   P  9e...14  an investor still pending R  9e...0c  a reviewer
--   A  9e...0a  an admin
\set ON_ERROR_STOP 1
reset role;

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

-- Refused calls are checked in a block, so a refusal does not stop the file.
create or replace function pg_temp.refused(label text, sql text, code text) returns void
language plpgsql as $$
begin
  execute sql;
  perform pg_temp.ok(label, false, 'call succeeded');
exception when others then
  perform pg_temp.ok(label, sqlstate = code, sqlstate || ' ' || sqlerrm);
end $$;

-- The kinds of one venture's entries, oldest first, read as the superuser.
create or replace function pg_temp.kinds(v uuid) returns text
language sql as $$
  select coalesce(string_agg(kind::text, ',' order by created_at, id), '') from public.activity_events where venture_id = v;
$$;

-- The two ventures these checks make.
create or replace function pg_temp.mine() returns uuid[]
language sql as $$
  select array['9f000000-0000-0000-0000-00000000000f', '9f000000-0000-0000-0000-000000000010']::uuid[];
$$;

insert into auth.users (id, email) values
  ('9e000000-0000-0000-0000-00000000000f', 'femi@activity.test'), ('9e000000-0000-0000-0000-000000000010', 'gift@activity.test'),
  ('9e000000-0000-0000-0000-000000000012', 'ife@activity.test'), ('9e000000-0000-0000-0000-000000000013', 'jo@activity.test'),
  ('9e000000-0000-0000-0000-000000000014', 'pat@activity.test'), ('9e000000-0000-0000-0000-00000000000c', 'rex@activity.test'),
  ('9e000000-0000-0000-0000-00000000000a', 'ada@activity.test');
insert into public.profiles (user_id, full_name, role, status) values
  ('9e000000-0000-0000-0000-00000000000f', 'Femi Farmer', 'founder', 'active'),
  ('9e000000-0000-0000-0000-000000000010', 'Gift Reader', 'founder', 'active'),
  ('9e000000-0000-0000-0000-000000000012', 'Ife Angel', 'investor', 'active'),
  ('9e000000-0000-0000-0000-000000000013', 'Jo Fund', 'investor', 'active'),
  ('9e000000-0000-0000-0000-000000000014', 'Pat Pending', 'investor', 'pending'),
  ('9e000000-0000-0000-0000-00000000000c', 'Rex Reviewer', 'reviewer', 'active'),
  ('9e000000-0000-0000-0000-00000000000a', 'Ada Admin', 'admin', 'active');
insert into public.investor_profiles (user_id, investor_type, firm, based_in, sectors, cheque_size, confirmed_statement) values
  ('9e000000-0000-0000-0000-000000000012', 'angel', 'Harbour Angels', 'GH', array['Agritech'], 'Prefer not to say', true),
  ('9e000000-0000-0000-0000-000000000013', 'fund', 'Savannah Seed', 'NG', array['Agritech'], 'Prefer not to say', true),
  ('9e000000-0000-0000-0000-000000000014', 'angel', null, 'other', array['Agritech'], 'Prefer not to say', true);

set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- what makes an entry
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('9f000000-0000-0000-0000-00000000000f', auth.uid(), 'Kola Farms', 'Agritech', 'GH', 'revenue');
insert into public.evidence (id, venture_id, signal_code, summary) values
  ('9f100000-0000-0000-0000-000000000001', '9f000000-0000-0000-0000-00000000000f', 'revenue', 'Twelve months of bank statements'),
  ('9f100000-0000-0000-0000-000000000002', '9f000000-0000-0000-0000-00000000000f', 'company_registration', 'Our registration certificate'),
  ('9f100000-0000-0000-0000-000000000003', '9f000000-0000-0000-0000-00000000000f', 'website_live', 'Our live shop');
reset role;
select pg_temp.ok('X1 creating a venture and adding evidence makes no entry',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = '', pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
set role authenticated;

insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
values ('9f000000-0000-0000-0000-00000000000f', '9e000000-0000-0000-0000-00000000000f/p1', 'video/mp4', 1000, 58,
        'We sell cassava flour to bakeries in Accra and Kumasi.');
update public.ventures set published_at = now() where id = '9f000000-0000-0000-0000-00000000000f';
update public.ventures set ask = '$80,000 to open a second mill' where id = '9f000000-0000-0000-0000-00000000000f';
update public.ventures set ask = '$90,000 to open a second mill' where id = '9f000000-0000-0000-0000-00000000000f';
reset role;
select pg_temp.ok('X2 a pitch, publishing and an ask each make one entry, and a second ask the same day makes none',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = 'pitch_added,published,ask_set',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
set role authenticated;

update public.pitches set transcript = 'We sell cassava flour to bakeries in Accra, Kumasi and Tamale.'
 where venture_id = '9f000000-0000-0000-0000-00000000000f';
update public.pitches set storage_path = '9e000000-0000-0000-0000-00000000000f/p2'
 where venture_id = '9f000000-0000-0000-0000-00000000000f';
update public.pitches set storage_path = '9e000000-0000-0000-0000-00000000000f/p3'
 where venture_id = '9f000000-0000-0000-0000-00000000000f';
reset role;
select pg_temp.ok('X3 a new transcript makes no entry, a new video makes one, and a second the same day makes none',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = 'pitch_added,published,ask_set,pitch_replaced',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
set role authenticated;

select public.declare_evidence('9f000000-0000-0000-0000-00000000000f', 'team_diversity', 'Three women and two men on the team.');
reset role;
select pg_temp.ok('X4 a statement the founder makes alone makes no entry',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = 'pitch_added,published,ask_set,pitch_replaced',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
update public.evidence set status = 'approved', lane = 'ai', decided_at = now() where id = '9f100000-0000-0000-0000-000000000003';
select pg_temp.ok('X5 an approval by the automatic check alone makes no entry',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = 'pitch_added,published,ask_set,pitch_replaced',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
insert into public.evidence (venture_id, signal_code, summary, status, lane, decided_at)
values ('9f000000-0000-0000-0000-00000000000f', 'product_stage', 'A signal rubric v3 does not hold', 'approved', 'human', now());
select pg_temp.ok('X5a evidence for a signal the active rubric does not hold makes no entry',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f') = 'pitch_added,published,ask_set,pitch_replaced',
  pg_temp.kinds('9f000000-0000-0000-0000-00000000000f'));
set role authenticated;

set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000c';
select public.decide_evidence('9f100000-0000-0000-0000-000000000001', 'approve', 'human', 'Compared with the bank statements');
select public.decide_evidence('9f100000-0000-0000-0000-000000000002', 'approve', 'government', 'Matched the company registry');
reset role;
select pg_temp.ok('X6 each approval in a lane investors see makes one entry, saying whether an outside source backs it',
  (select string_agg((detail->>'signal_code') || ':' || (detail->>'outside'), ',' order by id) from public.activity_events
    where venture_id = '9f000000-0000-0000-0000-00000000000f' and kind = 'evidence_approved') = 'revenue:false,company_registration:true',
  (select string_agg(detail::text, ',') from public.activity_events where kind = 'evidence_approved'));
set role authenticated;

-- Two investors ask. The founder accepts the angel and declines the fund.
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
insert into public.introductions (venture_id, note) values
  ('9f000000-0000-0000-0000-00000000000f', 'We back food processing in Ghana and would like to hear more.');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000013';
insert into public.introductions (venture_id, note) values
  ('9f000000-0000-0000-0000-00000000000f', 'Our fund invests in agritech across West Africa.');
reset role;
select pg_temp.ok('X7 a request for an introduction makes no entry',
  not exists (select 1 from public.activity_events where kind = 'introduction_accepted' and venture_id = '9f000000-0000-0000-0000-00000000000f'));
set role authenticated;
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
update public.introductions set status = 'accepted' where investor_id = '9e000000-0000-0000-0000-000000000012';
update public.introductions set status = 'declined' where investor_id = '9e000000-0000-0000-0000-000000000013';
reset role;
select pg_temp.ok('X8 only the accepted introduction makes an entry, and it keeps the investor''s type and nothing else',
  (select count(*) from public.activity_events where kind = 'introduction_accepted' and venture_id = '9f000000-0000-0000-0000-00000000000f') = 1
  and (select detail from public.activity_events where kind = 'introduction_accepted' and venture_id = '9f000000-0000-0000-0000-00000000000f') = '{"investor_type": "angel"}'::jsonb,
  (select string_agg(detail::text, ',') from public.activity_events where kind = 'introduction_accepted' and venture_id = '9f000000-0000-0000-0000-00000000000f'));
select pg_temp.ok('X9 no entry holds a name, a firm, a note, the ask or a summary',
  not exists (select 1 from public.activity_events
    where venture_id = any (pg_temp.mine()) and detail::text ~* '(Ife|Harbour|Savannah|Jo Fund|second mill|cassava|bank statements|registration certificate)'));
set role authenticated;

-- ---------------------------------------------------------------- who reads the feed
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000010';
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('9f000000-0000-0000-0000-000000000010', auth.uid(), 'Duka Books', 'Edtech', 'KE', 'mvp');
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript)
values ('9f000000-0000-0000-0000-000000000010', '9e000000-0000-0000-0000-000000000010/p1', 'video/mp4', 1000, 50,
        'We print exercise books for schools in Nairobi.');
select pg_temp.ok('X10 another founder reads Kola Farms'' seven entries, named, with sector and country',
  count(*) = 7 and bool_and(venture_name = 'Kola Farms' and sector = 'Agritech' and country = 'GH'), count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());
select pg_temp.ok('X11 an unpublished venture''s entries stay out of the feed, even for its founder',
  not exists (select 1 from public.activity_feed() where venture_id = '9f000000-0000-0000-0000-000000000010'));
select pg_temp.ok('X12 a founder reads their own unpublished venture''s entries by asking for it',
  (select string_agg(kind::text, ',' order by created_at desc, id desc) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-000000000010')) = 'pitch_added');
select pg_temp.refused('X13 a founder cannot read the table directly', 'select * from public.activity_events', '42501');
select pg_temp.refused('X14 a founder cannot write an entry directly',
  $q$insert into public.activity_events (venture_id, kind) values ('9f000000-0000-0000-0000-000000000010', 'published')$q$, '42501');
select pg_temp.refused('X15 a founder cannot call the function that writes entries',
  $q$select public.add_activity('9f000000-0000-0000-0000-000000000010', 'published')$q$, '42501');

set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
select pg_temp.ok('X16 an approved investor reads the same seven entries, newest first',
  count(*) = 7 and (array_agg(kind order by created_at desc, id desc))[1] = 'introduction_accepted'
  and (array_agg(kind order by created_at desc, id desc))[7] = 'pitch_added', count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());
select pg_temp.ok('X17 an investor cannot read an unpublished venture by asking for it',
  not exists (select 1 from public.activity_feed(p_venture => '9f000000-0000-0000-0000-000000000010')));
select pg_temp.ok('X18 the feed reads page by page',
  (select string_agg(kind::text, ',' order by created_at desc, id desc) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f', p_limit => 2)) = 'introduction_accepted,evidence_approved'
  and (select count(*) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f',
         p_before => (select min(created_at) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f', p_limit => 2)), p_limit => 100)) = 5);
select pg_temp.ok('X19 the feed reads what is new since an entry',
  (select string_agg(kind::text, ',' order by created_at desc, id desc) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f',
     p_after => (select created_at from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f') where kind = 'pitch_replaced'))) = 'introduction_accepted,evidence_approved,evidence_approved');
select pg_temp.refused('X20 an investor cannot read the table directly', 'select * from public.activity_events', '42501');

set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000014';
select pg_temp.refused('X21 a pending investor cannot read the feed', 'select * from public.activity_feed()', '42501');

set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000c';
select pg_temp.ok('X22 a reviewer reads the feed', count(*) = 7, count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());
select pg_temp.ok('X23 staff read an unpublished venture''s entries by asking for it',
  count(*) = 1, count(*)::text) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-000000000010');

reset role;
set role anon;
set request.jwt.claim.role = 'anon';
set request.jwt.claim.sub = '';
select pg_temp.refused('X24 a visitor cannot read the feed', 'select * from public.activity_feed()', '42501');
reset role;
set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- holds, hiding and suspension
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000a';
select public.admin_hide_venture('9f000000-0000-0000-0000-00000000000f', 'Checking a report about this profile.');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
select pg_temp.ok('X25 a profile an admin hides leaves the feed at once', count(*) = 0, count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
select pg_temp.ok('X26 its founder still reads its entries by asking for it',
  count(*) = 7, count(*)::text) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000a';
select public.admin_lift_hold('9f000000-0000-0000-0000-00000000000f');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
update public.ventures set published_at = now() where id = '9f000000-0000-0000-0000-00000000000f';
reset role;
select pg_temp.ok('X27 publishing again makes no second entry',
  (select count(*) from public.activity_events where venture_id = '9f000000-0000-0000-0000-00000000000f' and kind = 'published') = 1);
set role authenticated;
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
select pg_temp.ok('X28 the entries come back once the profile is published again', count(*) = 7, count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());

set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000a';
select public.admin_set_status('9e000000-0000-0000-0000-00000000000f', 'suspended', 'Checking a report.');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
select pg_temp.ok('X29 a suspended founder''s entries leave the feed', count(*) = 0, count(*)::text)
  from public.activity_feed(p_limit => 100) where venture_id = any (pg_temp.mine());
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
select pg_temp.refused('X30 a suspended founder cannot read the feed', 'select * from public.activity_feed()', '42501');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000a';
select public.admin_set_status('9e000000-0000-0000-0000-00000000000f', 'active', 'The report was not upheld.');
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
update public.ventures set published_at = now() where id = '9f000000-0000-0000-0000-00000000000f';

-- ---------------------------------------------------------------- the counts that replace posted updates
set request.jwt.claim.sub = '9e000000-0000-0000-0000-000000000012';
select pg_temp.ok('X31 discovery counts one active week for Kola Farms and dates its last activity from the newest entry',
  active_weeks = 1 and last_activity >= (select max(created_at) from public.activity_feed(p_venture => '9f000000-0000-0000-0000-00000000000f')),
  coalesce(active_weeks::text, 'null')) from public.discover_ventures() where name = 'Kola Farms';
reset role;
insert into public.activity_events (venture_id, kind, created_at) values
  ('9f000000-0000-0000-0000-00000000000f', 'ask_set', now() - interval '15 days'),
  ('9f000000-0000-0000-0000-00000000000f', 'ask_set', now() - interval '18 days'),
  ('9f000000-0000-0000-0000-00000000000f', 'ask_set', now() - interval '100 days');
set role authenticated;
select pg_temp.ok('X32 entries 15 and 18 days ago fall in one more week, and one 100 days ago is not counted',
  active_weeks = 2, coalesce(active_weeks::text, 'null')) from public.discover_ventures() where name = 'Kola Farms';
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000a';
select pg_temp.ok('X33 the staff founders list counts the same weeks',
  active_weeks = 2, coalesce(active_weeks::text, 'null')) from public.admin_ventures() where name = 'Kola Farms';
set request.jwt.claim.sub = '9e000000-0000-0000-0000-00000000000f';
select pg_temp.refused('X34 a founder can no longer post a progress update',
  $q$insert into public.venture_updates (venture_id, body) values ('9f000000-0000-0000-0000-00000000000f', 'We opened a second mill this week.')$q$,
  '42501');

reset role;
