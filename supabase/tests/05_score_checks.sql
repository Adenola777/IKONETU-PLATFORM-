-- Checks for migrations 20261020000001 (score v3) and 20261020000002 (the rubric v3 seed).
-- Each check prints PASS or FAIL with what it found. Run it after the migrations, as a
-- superuser, on its own or after 01 to 04. It makes its own people:
--   K  5a...01  founder of Kola Pay, published
--   L  5a...02  founder of Lagos Loop
--   M  5a...03  an approved investor
--   N  5a...04  a reviewer who still owns a venture, Nupe Foods
--   O  5a...05  a suspended founder of Oyo Crafts
\set ON_ERROR_STOP 1
reset role;

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

-- The stub creates service_role with no rights; a real Supabase project gives it the schema.
grant usage on schema public to service_role;

insert into auth.users (id) values
  ('5a000000-0000-0000-0000-000000000001'), ('5a000000-0000-0000-0000-000000000002'), ('5a000000-0000-0000-0000-000000000003'),
  ('5a000000-0000-0000-0000-000000000004'), ('5a000000-0000-0000-0000-000000000005');
insert into public.profiles (user_id, full_name, role, status) values
  ('5a000000-0000-0000-0000-000000000001', 'Kemi Founder', 'founder', 'active'),
  ('5a000000-0000-0000-0000-000000000002', 'Lanre Founder', 'founder', 'active'),
  ('5a000000-0000-0000-0000-000000000003', 'Musa Investor', 'investor', 'active'),
  ('5a000000-0000-0000-0000-000000000004', 'Nneka Reviewer', 'reviewer', 'active'),
  ('5a000000-0000-0000-0000-000000000005', 'Ola Founder', 'founder', 'suspended');
insert into public.investor_profiles (user_id, investor_type, based_in, sectors, cheque_size, confirmed_statement)
values ('5a000000-0000-0000-0000-000000000003', 'angel', 'NG', array['Fintech'], 'Prefer not to say', true);
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('5b000000-0000-0000-0000-000000000001', '5a000000-0000-0000-0000-000000000001', 'Kola Pay', 'Fintech', 'NG', 'revenue'),
  ('5b000000-0000-0000-0000-000000000002', '5a000000-0000-0000-0000-000000000002', 'Lagos Loop', 'Other', 'NG', 'idea'),
  ('5b000000-0000-0000-0000-000000000004', '5a000000-0000-0000-0000-000000000004', 'Nupe Foods', 'Agritech', 'NG', 'idea'),
  ('5b000000-0000-0000-0000-000000000005', '5a000000-0000-0000-0000-000000000005', 'Oyo Crafts', 'Other', 'NG', 'idea');
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript) values
  ('5b000000-0000-0000-0000-000000000001', '5a000000-0000-0000-0000-000000000001/p.mp4', 'video/mp4', 100, 70,
   'We let market traders take card payments on a phone.');
update public.ventures set published_at = now() where id = '5b000000-0000-0000-0000-000000000001';

-- S1 and S2: the rubric.
select pg_temp.ok('S1 rubric v3 is the only active rubric',
  (select array_agg(version) from public.rubric_versions where is_active) = array['v3']);
select pg_temp.ok('S2 rubric v3 has 175 signals, 12 categories and weights that add up to 100',
  (select count(*) from public.rubric_signals where rubric_version = 'v3') = 175
  and (select count(*) from public.rubric_categories where rubric_version = 'v3') = 12
  and (select sum(weight) from public.rubric_categories where rubric_version = 'v3' and alternative_to is null) = 100,
  (select count(*)::text from public.rubric_signals where rubric_version = 'v3'));

-- S3 to S8: self-declared signals.
set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000001';
select public.declare_evidence('5b000000-0000-0000-0000-000000000001', 'team_diversity', 'Two of our five staff are women.',
  '5e000000-0000-0000-0000-000000000001');
select pg_temp.ok('S3 a founder states a self-declared signal, and it is approved in the self lane',
  exists (select 1 from public.evidence where venture_id = '5b000000-0000-0000-0000-000000000001'
          and signal_code = 'team_diversity' and status = 'approved' and lane = 'self' and decided_at is not null));

do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000001', 'company_registration', 'We are registered with CAC.');
  perform pg_temp.ok('S4 a founder cannot state a signal a reviewer must check', false, 'call succeeded');
exception when others then perform pg_temp.ok('S4 a founder cannot state a signal a reviewer must check', sqlstate = '22023', sqlerrm);
end $$;
do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000001', 'next_of_kin', 'My sister');
  perform pg_temp.ok('S5 a statement under 10 characters is refused', false, 'call succeeded');
exception when others then perform pg_temp.ok('S5 a statement under 10 characters is refused', sqlstate = '22023', sqlerrm);
end $$;
do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000002', 'next_of_kin', 'My brother is my emergency contact.');
  perform pg_temp.ok('S6 a founder cannot make a statement for another venture', false, 'call succeeded');
exception when others then perform pg_temp.ok('S6 a founder cannot make a statement for another venture', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000001', 'team_diversity', 'Two of our five staff are women.',
    '5e000000-0000-0000-0000-000000000001');
  perform pg_temp.ok('S8 the same request key cannot make the statement twice', false, 'second call succeeded');
exception when unique_violation then perform pg_temp.ok('S8 the same request key cannot make the statement twice', true);
end $$;

set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000005';
do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000005', 'next_of_kin', 'My aunt is my emergency contact.');
  perform pg_temp.ok('S7 a suspended founder cannot make a statement', false, 'call succeeded');
exception when others then perform pg_temp.ok('S7 a suspended founder cannot make a statement', sqlstate = '42501', sqlerrm);
end $$;

set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000003';
select pg_temp.ok('S9 an approved investor does not see a founder''s own statement',
  not exists (select 1 from public.venture_evidence('5b000000-0000-0000-0000-000000000001') where signal_code = 'team_diversity')
  and exists (select 1 from public.ventures where id = '5b000000-0000-0000-0000-000000000001'));

-- S10 to S16: recording a score and the monthly record.
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000001';
do $$ begin
  perform public.record_score('5b000000-0000-0000-0000-000000000001', 1000, 'ELITE', '[]'::jsonb, 'v3');
  perform pg_temp.ok('S10 a founder cannot record their own score', false, 'call succeeded');
exception when others then perform pg_temp.ok('S10 a founder cannot record their own score', sqlstate = '42501', sqlerrm);
end $$;

reset role;
set role service_role;
set request.jwt.claim.role = 'service_role';
reset request.jwt.claim.sub;
select public.record_score('5b000000-0000-0000-0000-000000000001', 6, 'EARLY', '[{"category":"team"}]'::jsonb, 'v3', null,
  '{"T4": 100}'::jsonb);
reset role;
select pg_temp.ok('S11 the server records a score with its service role, and the month''s record is written',
  (select total from public.scores where venture_id = '5b000000-0000-0000-0000-000000000001') = 6
  and (select count(*) from public.score_snapshots where venture_id = '5b000000-0000-0000-0000-000000000001'
       and month = date_trunc('month', now() at time zone 'utc')::date and total = 6 and tiers = '{"T4": 100}'::jsonb) = 1);

set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000004';
select public.record_score('5b000000-0000-0000-0000-000000000001', 40, 'EARLY', '[]'::jsonb, 'v3');
reset role;
select pg_temp.ok('S12 a second score in the same month keeps one record, holding the newer total',
  (select count(*) from public.score_snapshots where venture_id = '5b000000-0000-0000-0000-000000000001') = 1
  and (select total from public.score_snapshots where venture_id = '5b000000-0000-0000-0000-000000000001') = 40
  and (select count(*) from public.score_events where venture_id = '5b000000-0000-0000-0000-000000000001') = 2);

set role authenticated;
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000004';
do $$ begin
  perform public.record_score('5b000000-0000-0000-0000-000000000004', 900, 'ELITE', '[]'::jsonb, 'v3');
  perform pg_temp.ok('S13 a reviewer cannot record the score of their own venture', false, 'call succeeded');
exception when others then perform pg_temp.ok('S13 a reviewer cannot record the score of their own venture', sqlstate = '42501', sqlerrm);
end $$;

set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000001';
select pg_temp.ok('S14 the founder reads their own monthly record', count(*) = 1, count(*)::text) from public.score_snapshots;
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000002';
select pg_temp.ok('S15 another founder reads no monthly record', count(*) = 0, count(*)::text) from public.score_snapshots;
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000003';
select pg_temp.ok('S15a an investor reads no monthly record', count(*) = 0, count(*)::text) from public.score_snapshots;

reset role;
insert into public.score_snapshots (venture_id, month, total, league, categories, rubric_version)
values ('5b000000-0000-0000-0000-000000000001', (date_trunc('month', now() at time zone 'utc') - interval '1 month')::date,
        20, 'EARLY', '[]'::jsonb, 'v3');
do $$ begin
  update public.score_snapshots set total = 999
   where venture_id = '5b000000-0000-0000-0000-000000000001' and month < date_trunc('month', now() at time zone 'utc')::date;
  perform pg_temp.ok('S16 the record of a month that has ended cannot change', false, 'update succeeded');
exception when others then perform pg_temp.ok('S16 the record of a month that has ended cannot change', sqlstate = '42501', sqlerrm);
end $$;

-- S17: a statement leaves the score to update until it is recorded.
set role authenticated;
set request.jwt.claim.role = 'authenticated';
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000002';
select public.declare_evidence('5b000000-0000-0000-0000-000000000002', 'industry_classification', 'We sell second-hand phones.');
set request.jwt.claim.sub = '5a000000-0000-0000-0000-000000000004';
select pg_temp.ok('S17 a statement whose score is not recorded yet appears on the staff list of scores to update',
  exists (select 1 from public.ventures_with_stale_scores() where venture_id = '5b000000-0000-0000-0000-000000000002'));

-- S18 and S19: a visitor.
reset role;
set role anon;
set request.jwt.claim.role = 'anon';
reset request.jwt.claim.sub;
do $$ begin
  perform public.declare_evidence('5b000000-0000-0000-0000-000000000001', 'next_of_kin', 'My aunt is my emergency contact.');
  perform pg_temp.ok('S18 a visitor cannot make a statement', false, 'call succeeded');
exception when others then perform pg_temp.ok('S18 a visitor cannot make a statement', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform public.record_score('5b000000-0000-0000-0000-000000000001', 1000, 'ELITE', '[]'::jsonb, 'v3');
  perform pg_temp.ok('S18a a visitor cannot record a score', false, 'call succeeded');
exception when others then perform pg_temp.ok('S18a a visitor cannot record a score', sqlstate = '42501', sqlerrm);
end $$;
do $$ begin
  perform count(*) from public.score_snapshots;
  perform pg_temp.ok('S19 a visitor cannot read the monthly records', false, 'read succeeded');
exception when others then perform pg_temp.ok('S19 a visitor cannot read the monthly records', sqlstate = '42501', sqlerrm);
end $$;
reset role;
