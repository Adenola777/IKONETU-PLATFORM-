-- Checks for migration 20261017000001 (the admin dashboard). Each check prints
-- PASS or FAIL with what it found. Run it after the migrations, as a
-- superuser, on its own or after 01 to 03. Counts are compared before and
-- after each change, so rows left by the earlier files do not matter. It makes
-- its own people:
--   A  9a...0a  an admin            B  9a...0b  a second admin
--   R  9a...0c  a reviewer
--   F  9a...0f  founder of Tola Farms, published, with reviewed evidence
--   G  9a...10  founder of Gidi Learn, with no pitch
--   H  9a...11  founder of Hausa Health, published, with no reviewed evidence
--   I  9a...12  an approved investor  J  9a...13  a second approved investor
\set ON_ERROR_STOP 1
reset role;

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

insert into auth.users (id, email) values
  ('9a000000-0000-0000-0000-00000000000a', 'ada@admin.test'), ('9a000000-0000-0000-0000-00000000000b', 'ben@admin.test'),
  ('9a000000-0000-0000-0000-00000000000c', 'rex@review.test'), ('9a000000-0000-0000-0000-00000000000f', 'femi@founder.test'),
  ('9a000000-0000-0000-0000-000000000010', 'gina@founder.test'), ('9a000000-0000-0000-0000-000000000011', 'hauwa@founder.test'),
  ('9a000000-0000-0000-0000-000000000012', 'ike@investor.test'), ('9a000000-0000-0000-0000-000000000013', 'jo@investor.test');
insert into public.profiles (user_id, full_name, role, status) values
  ('9a000000-0000-0000-0000-00000000000a', 'Ada Admin', 'admin', 'active'),
  ('9a000000-0000-0000-0000-00000000000b', 'Ben Admin', 'admin', 'active'),
  ('9a000000-0000-0000-0000-00000000000c', 'Rex Reviewer', 'reviewer', 'active'),
  ('9a000000-0000-0000-0000-00000000000f', 'Femi Founder', 'founder', 'active'),
  ('9a000000-0000-0000-0000-000000000010', 'Gina Founder', 'founder', 'active'),
  ('9a000000-0000-0000-0000-000000000011', 'Hauwa Founder', 'founder', 'active'),
  ('9a000000-0000-0000-0000-000000000012', 'Ike Investor', 'investor', 'active'),
  ('9a000000-0000-0000-0000-000000000013', 'Jo Investor', 'investor', 'active');
insert into public.investor_profiles (user_id, investor_type, based_in, sectors, cheque_size, confirmed_statement) values
  ('9a000000-0000-0000-0000-000000000012', 'angel', 'NG', array['Agritech'], 'Prefer not to say', true),
  ('9a000000-0000-0000-0000-000000000013', 'fund', 'KE', array['Health'], 'Prefer not to say', true);
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('9b000000-0000-0000-0000-00000000000f', '9a000000-0000-0000-0000-00000000000f', 'Tola Farms', 'Agritech', 'NG', 'revenue'),
  ('9b000000-0000-0000-0000-000000000010', '9a000000-0000-0000-0000-000000000010', 'Gidi Learn', 'Edtech', 'GH', 'mvp'),
  ('9b000000-0000-0000-0000-000000000011', '9a000000-0000-0000-0000-000000000011', 'Hausa Health', 'Health', 'KE', 'idea');
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript) values
  ('9b000000-0000-0000-0000-00000000000f', '9a000000-0000-0000-0000-00000000000f/p.mp4', 'video/mp4', 100, 60, 'We help smallholder farmers sell directly to schools.'),
  ('9b000000-0000-0000-0000-000000000011', '9a000000-0000-0000-0000-000000000011/p.mp4', 'video/mp4', 100, 60, 'We run mobile clinics for market traders in Nairobi.');
update public.ventures set published_at = now() where id in ('9b000000-0000-0000-0000-00000000000f', '9b000000-0000-0000-0000-000000000011');
insert into public.evidence (id, venture_id, signal_code, summary, status, lane, public_note, decided_at) values
  ('9c000000-0000-0000-0000-000000000001', '9b000000-0000-0000-0000-00000000000f', 'revenue', 'Six months of sales records',
   'approved', 'human', 'Compared the sales ledger with bank statements', now() - interval '1 hour');
insert into public.evidence (venture_id, signal_code, summary) values ('9b000000-0000-0000-0000-000000000011', 'website_live', 'Our booking page');

set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- who may read what
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
do $$ begin
  perform public.admin_overview();
  perform pg_temp.ok('D1 a founder cannot read the overview', false, 'call succeeded');
exception when others then perform pg_temp.ok('D1 a founder cannot read the overview', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.admin_ventures();
  perform pg_temp.ok('D2 a founder cannot list ventures', false, 'call succeeded');
exception when others then perform pg_temp.ok('D2 a founder cannot list ventures', sqlstate = '42501', sqlerrm);
end $$;

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000c';
select pg_temp.ok('D3 a reviewer reads the overview', (select count(*) from public.admin_overview()) = 1);
select pg_temp.ok('D4 a reviewer lists ventures with what each holds',
  exists (select 1 from public.admin_ventures('Tola', 'all') where name = 'Tola Farms' and has_pitch and evidence_total = 1
          and evidence_reviewed = 1 and founder_name = 'Femi Founder' and published_at is not null));
do $$ begin
  perform public.admin_accounts();
  perform pg_temp.ok('D5 a reviewer cannot list accounts and their email addresses', false, 'call succeeded');
exception when others then perform pg_temp.ok('D5 a reviewer cannot list accounts and their email addresses', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.admin_hide_venture('9b000000-0000-0000-0000-00000000000f', 'Reviewers may not hide profiles');
  perform pg_temp.ok('D6 a reviewer cannot hide a profile', false, 'call succeeded');
exception when others then perform pg_temp.ok('D6 a reviewer cannot hide a profile', sqlstate = '42501', sqlerrm);
end $$;
select pg_temp.ok('D7 a reviewer cannot read the audit log', (select count(*) from public.audit_log) = 0);

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
select pg_temp.ok('D8 an admin lists accounts with their email address',
  exists (select 1 from public.admin_accounts('femi@') where full_name = 'Femi Founder' and email = 'femi@founder.test'
          and venture_name = 'Tola Farms'));
select pg_temp.ok('D9 the founders list filters by state',
  not exists (select 1 from public.admin_ventures('Gidi', 'published'))
  and exists (select 1 from public.admin_ventures('Gidi', 'unpublished')));

-- ---------------------------------------------------------------- the north star
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000c';
create temp table before_counts as select * from public.admin_overview();
set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000012';
insert into public.introductions (id, venture_id, note) values
  ('9d000000-0000-0000-0000-000000000001', '9b000000-0000-0000-0000-00000000000f', 'We back farm-to-school supply and would like to talk.'),
  ('9d000000-0000-0000-0000-000000000002', '9b000000-0000-0000-0000-000000000011', 'We fund primary care for informal workers in Kenya.');
set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000013';
insert into public.introductions (id, venture_id, note) values
  ('9d000000-0000-0000-0000-000000000003', '9b000000-0000-0000-0000-00000000000f', 'Our fund looks at food supply chains across Africa.');
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
update public.introductions set status = 'accepted' where id = '9d000000-0000-0000-0000-000000000001';
insert into public.introduction_messages (introduction_id, sender_id, body) values
  ('9d000000-0000-0000-0000-000000000001', auth.uid(), 'Thank you. Tuesday works for me.');
set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000011';
update public.introductions set status = 'accepted' where id = '9d000000-0000-0000-0000-000000000002';

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000c';
select pg_temp.ok('N1 an accepted introduction to a founder with reviewed evidence counts toward the north star',
  (select north_star_30d from public.admin_overview()) = (select north_star_30d from before_counts) + 1,
  (select north_star_30d from public.admin_overview())::text);
select pg_temp.ok('N2 accepted introductions count both, and pending requests are counted apart',
  (select accepted_30d from public.admin_overview()) = (select accepted_30d from before_counts) + 2
  and (select introductions_pending from public.admin_overview()) = (select introductions_pending from before_counts) + 1);
select pg_temp.ok('N3 the north star by month ends with this month',
  (select north_star_months -> -1 ->> 'month' from public.admin_overview()) = to_char(now(), 'YYYY-MM')
  and jsonb_array_length((select north_star_months from public.admin_overview())) = 6);

-- ---------------------------------------------------------------- hiding a profile
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
do $$ begin
  perform public.admin_hide_venture('9b000000-0000-0000-0000-00000000000f', 'no');
  perform pg_temp.ok('M1 a hold needs a reason', false, 'call succeeded');
exception when others then perform pg_temp.ok('M1 a hold needs a reason', sqlstate = '22023', sqlerrm);
end $$;
select public.admin_hide_venture('9b000000-0000-0000-0000-00000000000f', 'The revenue figure on the profile does not match the reviewed records.');
select pg_temp.ok('M2 hiding takes the profile out of investors'' view and records the hold',
  (select published_at is null and hidden_at is not null and hidden_by = auth.uid() from public.ventures
   where id = '9b000000-0000-0000-0000-00000000000f'));
select pg_temp.ok('M3 the hold goes to the audit log with its reason',
  exists (select 1 from public.audit_log where action = 'venture.hide' and entity_id = '9b000000-0000-0000-0000-00000000000f'
          and actor_id = auth.uid() and after ->> 'reason' like 'The revenue figure%'));
do $$ begin
  perform public.admin_hide_venture('9b000000-0000-0000-0000-00000000000f', 'A second hold on the same profile');
  perform pg_temp.ok('M4 a profile cannot be held twice', false, 'call succeeded');
exception when others then perform pg_temp.ok('M4 a profile cannot be held twice', sqlstate = 'P0001', sqlerrm);
end $$;

set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000012';
select pg_temp.ok('M5 an investor no longer sees the held profile',
  not exists (select 1 from public.ventures where id = '9b000000-0000-0000-0000-00000000000f')
  and not exists (select 1 from public.discover_ventures() where venture_id = '9b000000-0000-0000-0000-00000000000f'));

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
select pg_temp.ok('M6 the founder reads the reason on their own venture',
  (select hidden_reason from public.ventures where id = '9b000000-0000-0000-0000-00000000000f') like 'The revenue figure%');
do $$ begin
  update public.ventures set published_at = now() where id = '9b000000-0000-0000-0000-00000000000f';
  perform pg_temp.ok('M7 the founder cannot publish a held profile', false, 'update succeeded');
exception when others then perform pg_temp.ok('M7 the founder cannot publish a held profile', sqlstate = 'P0001', sqlerrm);
end $$;
do $$ begin
  update public.ventures set hidden_at = null, hidden_reason = null, hidden_by = null where id = '9b000000-0000-0000-0000-00000000000f';
  perform pg_temp.ok('M8 the founder cannot lift the hold', false, 'update succeeded');
exception when others then perform pg_temp.ok('M8 the founder cannot lift the hold', sqlstate = '42501', sqlerrm);
end $$;

set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000010';
do $$ begin
  insert into public.ventures (founder_id, name, sector, country, stage, published_at)
  values (auth.uid(), 'Gidi Learn Two', 'Edtech', 'GH', 'idea', now());
  perform pg_temp.ok('M9 a venture cannot be created already published without a pitch', false, 'insert succeeded');
exception when others then perform pg_temp.ok('M9 a venture cannot be created already published without a pitch', sqlstate = 'P0001', sqlerrm);
end $$;
do $$ begin
  insert into public.ventures (founder_id, name, sector, country, stage, hidden_at, hidden_reason)
  values (auth.uid(), 'Gidi Learn Three', 'Edtech', 'GH', 'idea', now(), 'Set by the founder');
  perform pg_temp.ok('M10 a founder cannot create a venture with a hold of their own', false, 'insert succeeded');
exception when others then perform pg_temp.ok('M10 a founder cannot create a venture with a hold of their own', sqlstate = '42501', sqlerrm);
end $$;

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
select public.admin_lift_hold('9b000000-0000-0000-0000-00000000000f', 'The founder corrected the revenue figure.');
select pg_temp.ok('M11 lifting the hold clears it, keeps the profile unpublished, and is audited',
  (select hidden_at is null and hidden_reason is null and published_at is null from public.ventures
   where id = '9b000000-0000-0000-0000-00000000000f')
  and exists (select 1 from public.audit_log where action = 'venture.lift_hold' and entity_id = '9b000000-0000-0000-0000-00000000000f'));
do $$ begin
  perform public.admin_lift_hold('9b000000-0000-0000-0000-00000000000f');
  perform pg_temp.ok('M12 a hold that is not there cannot be lifted', false, 'call succeeded');
exception when others then perform pg_temp.ok('M12 a hold that is not there cannot be lifted', sqlstate = 'P0001', sqlerrm);
end $$;
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
update public.ventures set published_at = now() where id = '9b000000-0000-0000-0000-00000000000f';
select pg_temp.ok('M13 the founder can publish again once the hold is lifted',
  (select published_at is not null from public.ventures where id = '9b000000-0000-0000-0000-00000000000f'));

-- ---------------------------------------------------------------- roles
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
do $$ begin
  perform public.admin_set_role(auth.uid(), 'reviewer');
  perform pg_temp.ok('P1 an admin cannot change their own role', false, 'call succeeded');
exception when others then perform pg_temp.ok('P1 an admin cannot change their own role', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.admin_set_role('9a000000-0000-0000-0000-00000000000c', 'founder');
  perform pg_temp.ok('P2 a person without a venture cannot become a founder', false, 'call succeeded');
exception when others then perform pg_temp.ok('P2 a person without a venture cannot become a founder', sqlstate = 'P0001', sqlerrm);
end $$;
do $$ begin
  perform public.admin_set_role('9a000000-0000-0000-0000-000000000011', 'investor');
  perform pg_temp.ok('P3 a person without an investor profile cannot become an investor', false, 'call succeeded');
exception when others then perform pg_temp.ok('P3 a person without an investor profile cannot become an investor', sqlstate = 'P0001', sqlerrm);
end $$;
do $$ begin
  perform public.admin_set_role('9a000000-0000-0000-0000-000000000011', 'mentor');
  perform pg_temp.ok('P4 the mentor role cannot be given yet', false, 'call succeeded');
exception when others then perform pg_temp.ok('P4 the mentor role cannot be given yet', sqlstate = '22023', sqlerrm);
end $$;
select public.admin_set_role('9a000000-0000-0000-0000-000000000011', 'reviewer', 'Joins the review team.');
select pg_temp.ok('P5 a founder made a reviewer is no longer visible to investors',
  (select role from public.profiles where user_id = '9a000000-0000-0000-0000-000000000011') = 'reviewer'
  and (select published_at is null from public.ventures where id = '9b000000-0000-0000-0000-000000000011')
  and exists (select 1 from public.audit_log where action = 'account.role' and entity_id = '9a000000-0000-0000-0000-000000000011'
              and after ->> 'role' = 'reviewer' and (after ->> 'profiles_hidden')::int = 1));
set request.jwt.claim.sub = '9a000000-0000-0000-0000-000000000011';
do $$ begin
  insert into public.evidence (venture_id, signal_code, summary) values ('9b000000-0000-0000-0000-000000000011', 'team', 'Our clinical lead');
  perform pg_temp.ok('P6 a reviewer cannot add evidence to the venture they once ran', false, 'insert succeeded');
exception when others then perform pg_temp.ok('P6 a reviewer cannot add evidence to the venture they once ran', sqlstate = '42501', sqlerrm);
end $$;
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
select public.admin_set_role('9a000000-0000-0000-0000-000000000011', 'founder');
select pg_temp.ok('P7 the same person can be made a founder again',
  (select role from public.profiles where user_id = '9a000000-0000-0000-0000-000000000011') = 'founder');
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000c';
do $$ begin
  perform public.admin_set_role('9a000000-0000-0000-0000-000000000010', 'reviewer');
  perform pg_temp.ok('P8 a reviewer cannot change a role', false, 'call succeeded');
exception when others then perform pg_temp.ok('P8 a reviewer cannot change a role', sqlstate = '42501', sqlerrm);
end $$;

-- ---------------------------------------------------------------- suspension
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
do $$ begin
  perform public.admin_set_status(auth.uid(), 'suspended', 'Testing a suspension of myself');
  perform pg_temp.ok('S1 an admin cannot suspend themselves', false, 'call succeeded');
exception when others then perform pg_temp.ok('S1 an admin cannot suspend themselves', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.admin_set_status('9a000000-0000-0000-0000-00000000000f', 'suspended');
  perform pg_temp.ok('S2 a suspension needs a reason', false, 'call succeeded');
exception when others then perform pg_temp.ok('S2 a suspension needs a reason', sqlstate = '22023', sqlerrm);
end $$;
select public.admin_set_status('9a000000-0000-0000-0000-00000000000f', 'suspended', 'Reported for misleading investors.');
select pg_temp.ok('S3 suspending a founder takes their profile out of investors'' view and is audited',
  (select status from public.profiles where user_id = '9a000000-0000-0000-0000-00000000000f') = 'suspended'
  and (select published_at is null from public.ventures where id = '9b000000-0000-0000-0000-00000000000f')
  and exists (select 1 from public.audit_log where action = 'account.suspend' and entity_id = '9a000000-0000-0000-0000-00000000000f'
              and after ->> 'reason' = 'Reported for misleading investors.'));

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
do $$ begin
  insert into public.evidence (venture_id, signal_code, summary) values ('9b000000-0000-0000-0000-00000000000f', 'team', 'Our farm manager');
  perform pg_temp.ok('S4 a suspended founder cannot add evidence', false, 'insert succeeded');
exception when others then perform pg_temp.ok('S4 a suspended founder cannot add evidence', sqlstate = '42501', sqlerrm);
end $$;
update public.ventures set published_at = now(), name = 'Tola Farms Renamed' where id = '9b000000-0000-0000-0000-00000000000f';
update public.introductions set status = 'accepted' where id = '9d000000-0000-0000-0000-000000000003';
do $$ begin
  insert into public.introduction_messages (introduction_id, sender_id, body)
  values ('9d000000-0000-0000-0000-000000000001', auth.uid(), 'A message sent while suspended.');
  perform pg_temp.ok('S5 a suspended founder cannot send a message', false, 'insert succeeded');
exception when others then perform pg_temp.ok('S5 a suspended founder cannot send a message', sqlstate = '42501', sqlerrm);
end $$;
reset role;
select pg_temp.ok('S6 a suspended founder cannot publish, rename the venture or answer a request',
  (select published_at is null and name = 'Tola Farms' from public.ventures where id = '9b000000-0000-0000-0000-00000000000f')
  and (select status from public.introductions where id = '9d000000-0000-0000-0000-000000000003') = 'pending');
set role authenticated;
set request.jwt.claim.role = 'authenticated';

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
select public.admin_set_status('9a000000-0000-0000-0000-00000000000f', 'active', 'The report was not upheld.');
select pg_temp.ok('S7 making the founder active again does not publish the profile',
  (select status from public.profiles where user_id = '9a000000-0000-0000-0000-00000000000f') = 'active'
  and (select published_at is null from public.ventures where id = '9b000000-0000-0000-0000-00000000000f')
  and exists (select 1 from public.audit_log where action = 'account.reactivate' and entity_id = '9a000000-0000-0000-0000-00000000000f'));
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000f';
insert into public.venture_updates (venture_id, body) values ('9b000000-0000-0000-0000-00000000000f', 'We are back and supplying four schools.');
select pg_temp.ok('S8 an active founder writes to their venture again',
  exists (select 1 from public.venture_updates where body = 'We are back and supplying four schools.'));

set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000a';
select public.admin_set_status('9a000000-0000-0000-0000-00000000000b', 'suspended', 'Left the company.');
set request.jwt.claim.sub = '9a000000-0000-0000-0000-00000000000b';
do $$ begin
  perform public.admin_overview();
  perform pg_temp.ok('S9 a suspended admin loses access to the admin functions', false, 'call succeeded');
exception when others then perform pg_temp.ok('S9 a suspended admin loses access to the admin functions', sqlstate = '42501', sqlerrm);
end $$;

-- ---------------------------------------------------------------- visitors
reset role;
set role anon;
set request.jwt.claim.role = 'anon';
set request.jwt.claim.sub = '';
do $$ begin
  perform public.admin_overview();
  perform pg_temp.ok('V1 a visitor who is not signed in cannot call the admin functions', false, 'call succeeded');
exception when insufficient_privilege then perform pg_temp.ok('V1 a visitor who is not signed in cannot call the admin functions', true);
end $$;
reset role;
