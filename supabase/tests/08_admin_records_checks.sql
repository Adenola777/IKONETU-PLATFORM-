-- Checks for migration 20261027000002 (the admin records). Each check prints
-- PASS or FAIL with what it found. Run it after the migrations, as a
-- superuser, on its own or after 01 to 07. It makes its own people and its own
-- made-up records, and counts only those, so other files' rows do not count:
--   A  ad...0a  an admin              B  ad...0b  a second admin
--   S  ad...0d  a suspended admin     R  ad...0c  a reviewer
--   F  ad...0f  founder of Pilot Pay  G  ad...10  founder of Second Mill
--   I  ad...12  an approved investor  J  ad...13  a second approved investor
--   P  ad...14  an investor with no venture, made staff and then removed
--   U  ad...30  a sign-up with its email confirmed and no role
--   V  ad...31  a sign-up with its email not confirmed
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

create or replace function pg_temp.as_user(u text) returns void
language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub', u, false);
  perform set_config('request.jwt.claim.role', 'authenticated', false);
end $$;

-- What the dashboard counted before these checks added anything.
-- What each removal from the staff list answered.
create temp table removed (who text, result text);
grant all on removed to authenticated;

create temp table base as
  select (select count(*) from public.founder_register where not sample) as founders,
         (select count(*) from public.investor_register) as investors;
grant select on base to authenticated;

insert into auth.users (id, email, email_confirmed_at) values
  ('ad000000-0000-0000-0000-00000000000a', 'ada@records.test', now()), ('ad000000-0000-0000-0000-00000000000b', 'bola@records.test', now()),
  ('ad000000-0000-0000-0000-00000000000d', 'sade@records.test', now()), ('ad000000-0000-0000-0000-00000000000c', 'rita@records.test', now()),
  ('ad000000-0000-0000-0000-00000000000f', 'fola@records.test', now()), ('ad000000-0000-0000-0000-000000000010', 'gbenga@records.test', now()),
  ('ad000000-0000-0000-0000-000000000012', 'iyke@records.test', now()), ('ad000000-0000-0000-0000-000000000013', 'jide@records.test', now()),
  ('ad000000-0000-0000-0000-000000000014', 'pam@records.test', now());
insert into auth.users (id, email, created_at, email_confirmed_at) values
  ('ad000000-0000-0000-0000-000000000030', 'una@records.test', '2026-10-06 09:00+00', '2026-10-06 09:01+00'),
  ('ad000000-0000-0000-0000-000000000031', 'vic@records.test', '2026-10-06 10:00+00', null);
insert into public.profiles (user_id, full_name, role, status) values
  ('ad000000-0000-0000-0000-00000000000a', 'Ada Admin', 'admin', 'active'),
  ('ad000000-0000-0000-0000-00000000000b', 'Bola Admin', 'admin', 'active'),
  ('ad000000-0000-0000-0000-00000000000d', 'Sade Admin', 'admin', 'suspended'),
  ('ad000000-0000-0000-0000-00000000000c', 'Rita Reviewer', 'reviewer', 'active'),
  ('ad000000-0000-0000-0000-00000000000f', 'Fola Founder', 'founder', 'active'),
  ('ad000000-0000-0000-0000-000000000010', 'Gbenga Founder', 'founder', 'active'),
  ('ad000000-0000-0000-0000-000000000012', 'Iyke Investor', 'investor', 'active'),
  ('ad000000-0000-0000-0000-000000000013', 'Jide Investor', 'investor', 'active'),
  ('ad000000-0000-0000-0000-000000000014', 'Pam Investor', 'investor', 'active');
insert into public.investor_profiles (user_id, investor_type, firm, based_in, sectors, cheque_size, confirmed_statement) values
  ('ad000000-0000-0000-0000-000000000012', 'angel', null, 'NG', array['Fintech'], 'Prefer not to say', true),
  ('ad000000-0000-0000-0000-000000000013', 'fund', 'Delta Seed', 'GH', array['Fintech'], 'Prefer not to say', true),
  ('ad000000-0000-0000-0000-000000000014', 'angel', null, 'KE', array['Fintech'], 'Prefer not to say', true);

-- Two published ventures. Fola's pitch is 40 MB and 80 seconds, inside the rules it was added under.
insert into public.ventures (id, founder_id, name, sector, country, stage) values
  ('ae000000-0000-0000-0000-00000000000f', 'ad000000-0000-0000-0000-00000000000f', 'Pilot Pay', 'Fintech', 'NG', 'revenue'),
  ('ae000000-0000-0000-0000-000000000010', 'ad000000-0000-0000-0000-000000000010', 'Second Mill', 'Agritech', 'GH', 'mvp');
insert into public.pitches (venture_id, storage_path, mime_type, size_bytes, duration_seconds, transcript) values
  ('ae000000-0000-0000-0000-00000000000f', 'ad000000-0000-0000-0000-00000000000f/p1.mp4', 'video/mp4', 41943040, 80,
   'We help market traders take payments by phone.'),
  ('ae000000-0000-0000-0000-000000000010', 'ad000000-0000-0000-0000-000000000010/p1.mp4', 'video/mp4', 1000, 30,
   'We mill cassava for bakeries near Kumasi.');
update public.ventures set published_at = now() where id in ('ae000000-0000-0000-0000-00000000000f', 'ae000000-0000-0000-0000-000000000010');

-- Made-up register records: three founders, one sample founder, two register investors.
insert into public.founder_register (record_id, sample, full_name, email, phone, country, country_key, university, startup,
  sector, stage, amount, problem, support, joined_at, last_response_at) values
  ('p901', false, 'Name One', 'one@register.test', '+2330000001', 'GHANA', 'Ghana', 'University of Ghana', 'Pilot One', 'Fintech',
   'Idea stage', '$1,000', 'Traders lose sales when buyers carry no cash.', array['Financial support', 'Mentorship support'],
   '2026-01-13 21:16:55+00', '2026-02-01 08:00:00+00'),
  ('p902', false, 'Name Two', 'two@register.test', '', 'Nigerian', 'Nigeria', 'university of ghana', 'Pilot Two', 'Agritech',
   'MVP', '', '', array['Financial support'], '2026-02-10 10:00:00+00', '2026-02-10 10:00:00+00'),
  ('p903', false, 'Name Three', 'three@register.test', '', 'Kenya', 'Kenya', '', 'Pilot Three', 'Health',
   '', '', '', array['Legal support'], '2026-03-05 12:00:00+00', '2026-03-05 12:00:00+00'),
  ('s91', true, 'Sample Founder', 'sample@example.com', '', 'Kenya', 'Kenya', '', 'Sample Books', 'Fintech',
   '', '', '', '{}', '2026-07-04 14:05:00+00', '2026-07-04 14:05:00+00');
insert into public.founder_register_responses (response_id, record_id, responded_at, full_name, email, startup, sector) values
  ('f901', 'p901', '2026-01-13 21:16:55+00', 'Name One First', 'one@register.test', 'Pilot One', 'Fintech'),
  ('f902', 'p901', '2026-02-01 08:00:00+00', 'Name One', 'one@register.test', 'Pilot One Again', 'Fintech'),
  ('f903', 'p902', '2026-02-10 10:00:00+00', 'Name Two', 'two@register.test', 'Pilot Two', 'Agritech'),
  ('f904', 'p903', '2026-03-05 12:00:00+00', 'Name Three', 'three@register.test', 'Pilot Three', 'Health');
insert into public.investor_register (register_no, full_name, registered_on) values
  ('901', 'Register Investor One', '2026-07-01'), ('902', 'Register Investor Two', '2026-08-01');
insert into public.register_introductions (intro_id, sample, investor_no, record_id, made_on) values
  ('n901', false, '901', 'p901', '2026-10-24'), ('n902', false, '902', 'p902', '2026-10-24'),
  ('n903', false, '901', 'p903', '2026-10-24');
insert into public.register_introductions (intro_id, sample, investor_name, investor_registered_on, record_id, made_on,
  status, messages, accepted_on) values
  ('s901', true, 'Sample Investor, Sample Fund', '2026-07-01', 's91', '2026-07-12', 'accepted', 5, '2026-07-13');
insert into public.pitch_video_files (video_id, file_name, file_type, size_text, folder, added_on, drive_url) values
  ('t901', 'Pilot 1.MOV', 'MOV', '47.9 MB', 'All_Videos', '2026-10-25', 'https://drive.google.com/file/d/abc901/view'),
  ('t902', 'Pilot 2.mp4', 'MP4', '136 KB', 'All_Videos / Website_clips', '2026-10-25', 'https://drive.google.com/file/d/abc902/view');

set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- who may read and change
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000f');
select pg_temp.refused('M1 a founder cannot read the founder register', 'select * from public.admin_founder_records()', '42501');
select pg_temp.refused('M1a a founder cannot read the dashboard', 'select public.admin_dashboard()', '42501');
select pg_temp.refused('M1b a founder cannot read the settings', 'select * from public.admin_settings()', '42501');
select pg_temp.refused('M1c a founder cannot read the founder register table', 'select * from public.founder_register', '42501');
select pg_temp.refused('M1d a founder cannot read the responses table', 'select * from public.founder_register_responses', '42501');
select pg_temp.refused('M1e a founder cannot read the introductions between the registers', 'select * from public.register_introductions', '42501');
select pg_temp.refused('M1f a founder cannot read the pitch video files', 'select * from public.pitch_video_files', '42501');
select pg_temp.refused('M1g a founder cannot read the reports table', 'select * from public.reports', '42501');
select pg_temp.refused('M1h a founder cannot read the settings table', 'select * from public.platform_settings', '42501');
select pg_temp.refused('M1i a founder cannot change the settings table',
  'update public.platform_settings set mode = ''maintenance''', '42501');
select pg_temp.refused('M1j a founder cannot read the imports', 'select * from public.register_imports', '42501');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M2 a reviewer cannot read the founder register', 'select * from public.admin_founder_records()', '42501');
select pg_temp.refused('M2a a reviewer cannot read the dashboard', 'select public.admin_dashboard()', '42501');
select pg_temp.as_user('ad000000-0000-0000-0000-000000000012');
select pg_temp.refused('M3 an approved investor cannot read the introductions between the registers',
  'select * from public.admin_register_introductions()', '42501');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000d');
select pg_temp.refused('M4 a suspended admin cannot read the dashboard', 'select public.admin_dashboard()', '42501');
select pg_temp.refused('M4a a suspended admin cannot read the founder register', 'select * from public.admin_founder_records()', '42501');
reset role;
set role anon;
set request.jwt.claim.role = 'anon';
set request.jwt.claim.sub = '';
select pg_temp.refused('M5 a visitor cannot call the founder register function', 'select * from public.admin_founder_records()', '42501');
select pg_temp.refused('M5a a visitor cannot read the founder register table', 'select * from public.founder_register', '42501');
select pg_temp.ok('M6 a visitor reads the platform status, which starts live',
  (select mode = 'live' and pitch_max_mb = 50 and introductions_per_day = 10 from public.platform_status()));
reset role;
set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- the founder register
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M10 the founder register lists the register founders and not the sample founder',
  (select count(*) from public.admin_founder_records() where record_id in ('p901', 'p902', 'p903')) = 3
  and not exists (select 1 from public.admin_founder_records() where record_id = 's91'));
select pg_temp.ok('M11 the long answers come only for the export',
  (select problem is null and stage = 'Idea stage' from public.admin_founder_records() where record_id = 'p901')
  and (select problem = 'Traders lose sales when buyers carry no cash.' from public.admin_founder_records(true) where record_id = 'p901'));
select pg_temp.ok('M12 a founder who sent the form twice has one record and two responses',
  (select responses from public.admin_founder_records() where record_id = 'p901') = 2);
select pg_temp.ok('M13 a founder with no video reads as none',
  (select video_status from public.admin_founder_records() where record_id = 'p901') = 'none');
reset role;
update public.pitch_video_files set record_id = 'p901' where video_id = 't901';
set role authenticated;
select pg_temp.ok('M13a a founder whose video waits for review reads as pending',
  (select video_status from public.admin_founder_records() where record_id = 'p901') = 'pending');
select pg_temp.ok('M14 one record reads with its responses in order and its introduction with the register name',
  (select (r ->> 'full_name') = 'Name One'
      and jsonb_array_length(r -> 'responses') = 2
      and (r -> 'responses' -> 0 ->> 'response_id') = 'f901'
      and (r -> 'introductions' -> 0 ->> 'investor_name') = 'Register Investor One'
      and (r -> 'video' ->> 'video_id') = 't901'
   from public.admin_founder_record('p901') r));
select pg_temp.ok('M14a the sample record reads as sample, with the sample investor named',
  (select (r ->> 'sample')::boolean and (r -> 'introductions' -> 0 ->> 'investor_name') = 'Sample Investor, Sample Fund'
   from public.admin_founder_record('s91') r));
select pg_temp.ok('M14b a record that does not exist reads as null', public.admin_founder_record('p999') is null);
select public.admin_founder_record_delete('p903');
reset role;
select pg_temp.ok('M15 deleting a record removes its responses and its introductions',
  not exists (select 1 from public.founder_register where record_id = 'p903')
  and not exists (select 1 from public.founder_register_responses where record_id = 'p903')
  and not exists (select 1 from public.register_introductions where record_id = 'p903'));
select pg_temp.ok('M15a the audit log keeps the record number and counts, and none of the personal data',
  (select count(*) from public.audit_log
    where action = 'register.founder_delete' and entity_id = 'p903' and actor_id = 'ad000000-0000-0000-0000-00000000000a'
      and before = '{"responses": 1, "introductions": 1, "sample": false}'::jsonb
      and before::text not like '%Name Three%' and before::text not like '%three@register%') = 1);
set role authenticated;
select pg_temp.refused('M16 deleting a record that does not exist is refused', $q$select public.admin_founder_record_delete('p903')$q$, 'P0002');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M17 a reviewer cannot delete a record', $q$select public.admin_founder_record_delete('p902')$q$, '42501');

-- ---------------------------------------------------------------- sign-ups not finished
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M20 the sign-ups with no role are listed, saying whether the email was confirmed',
  (select array_agg(email || ':' || email_confirmed order by email) from public.admin_unfinished_signups()
    where email like '%@records.test') = array['una@records.test:true', 'vic@records.test:false']);
select pg_temp.ok('M21 a person with a role is not listed',
  not exists (select 1 from public.admin_unfinished_signups() where email = 'fola@records.test'));
select pg_temp.refused('M22 a person with a role cannot be removed here',
  $q$select public.admin_remove_signup('ad000000-0000-0000-0000-00000000000f')$q$, 'P0001');
select pg_temp.refused('M23 nobody removes their own account here',
  $q$select public.admin_remove_signup('ad000000-0000-0000-0000-00000000000a')$q$, '42501');
select public.admin_remove_signup('ad000000-0000-0000-0000-000000000030');
reset role;
select pg_temp.ok('M24 removing a sign-up removes the account, and the audit log keeps no email address',
  not exists (select 1 from auth.users where id = 'ad000000-0000-0000-0000-000000000030')
  and (select count(*) from public.audit_log where action = 'account.remove_signup'
        and entity_id = 'ad000000-0000-0000-0000-000000000030' and before = '{"email_confirmed": true}'::jsonb) = 1);
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000f');
select pg_temp.refused('M25 a founder cannot list sign-ups', 'select * from public.admin_unfinished_signups()', '42501');
select pg_temp.refused('M25a a founder cannot remove a sign-up',
  $q$select public.admin_remove_signup('ad000000-0000-0000-0000-000000000031')$q$, '42501');

-- ---------------------------------------------------------------- linking the investor register
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select public.admin_register_link('901', '  IYKE@Records.test ');
select pg_temp.ok('M30 a register entry links to the investor account by its email, in any case',
  (select account_id = 'ad000000-0000-0000-0000-000000000012' and account_name = 'Iyke Investor' and account_email = 'iyke@records.test'
   from public.admin_register('901')));
select pg_temp.refused('M31 an account linked to one entry cannot be linked to another',
  $q$select public.admin_register_link('902', 'iyke@records.test')$q$, 'P0001');
select pg_temp.refused('M32 an email that is not an investor account is refused',
  $q$select public.admin_register_link('902', 'fola@records.test')$q$, 'P0002');
select pg_temp.refused('M33 a linked entry cannot be linked again', $q$select public.admin_register_link('901', 'jide@records.test')$q$, 'P0001');
select pg_temp.ok('M34 the register filters by account',
  (select array_agg(register_no) from public.admin_register(null, null, 100, 0, 'linked') where register_no in ('901', '902')) = array['901']
  and (select array_agg(register_no) from public.admin_register(null, null, 100, 0, 'not') where register_no in ('901', '902')) = array['902']);
select pg_temp.ok('M35 each entry counts the introductions made from it',
  (select introductions from public.admin_register('901')) = 1 and (select introductions from public.admin_register('902')) = 1);
select public.admin_register_unlink('901');
select pg_temp.ok('M36 an entry unlinks',
  (select account_id is null and linked_at is null from public.admin_register('901')));
select pg_temp.refused('M36a an entry with no link cannot be unlinked', $q$select public.admin_register_unlink('901')$q$, 'P0001');
reset role;
select pg_temp.ok('M37 linking and unlinking are in the audit log',
  (select count(*) from public.audit_log where entity = 'investor_register' and entity_id = '901'
     and action in ('register.link', 'register.unlink') and actor_id = 'ad000000-0000-0000-0000-00000000000a') = 2);
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M38 a reviewer cannot link the register', $q$select public.admin_register_link('902', 'jide@records.test')$q$, '42501');

-- ---------------------------------------------------------------- introductions between the registers
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M40 the introductions name the register investor, or the sample investor',
  (select array_agg(intro_id || ':' || investor_name || ':' || founder_name order by intro_id)
   from public.admin_register_introductions() where intro_id in ('n901', 'n902', 's901'))
  = array['n901:Register Investor One:Name One', 'n902:Register Investor Two:Name Two', 's901:Sample Investor, Sample Fund:Sample Founder']);
select public.admin_register_introduction_status('n901', 'accepted');
select pg_temp.ok('M41 a pending introduction is marked accepted',
  (select status from public.admin_register_introductions('n901')) = 'accepted');
select pg_temp.refused('M42 an accepted introduction cannot be marked declined',
  $q$select public.admin_register_introduction_status('n901', 'declined')$q$, 'P0001');
select public.admin_register_introduction_status('n901', 'pending');
select pg_temp.ok('M43 an accepted introduction returns to pending', (select status from public.admin_register_introductions('n901')) = 'pending');
select pg_temp.refused('M44 a pending introduction cannot be marked pending',
  $q$select public.admin_register_introduction_status('n901', 'pending')$q$, 'P0001');
select pg_temp.refused('M44a an introduction that does not exist is refused',
  $q$select public.admin_register_introduction_status('n999', 'accepted')$q$, 'P0002');
reset role;
select pg_temp.ok('M45 each change is in the audit log, which is the history',
  (select array_agg((before ->> 'status') || '>' || (after ->> 'status') order by id) from public.audit_log
    where action = 'introduction.status' and entity_id = 'n901') = array['pending>accepted', 'accepted>pending']);
select pg_temp.refused('M46 a sample introduction cannot join a register founder',
  $q$insert into public.register_introductions (intro_id, sample, investor_name, investor_registered_on, record_id, made_on)
     values ('s902', true, 'Sample Investor', '2026-07-01', 'p901', '2026-07-12')$q$, '23514');
select pg_temp.refused('M46a a register introduction needs a register number',
  $q$insert into public.register_introductions (intro_id, sample, record_id, made_on) values ('n904', false, 'p901', '2026-10-24')$q$, '23514');
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M47 a reviewer cannot change an introduction',
  $q$select public.admin_register_introduction_status('n902', 'accepted')$q$, '42501');

-- ---------------------------------------------------------------- pitch videos in Google Drive
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.refused('M50 approving with three of the four checks is refused',
  $q$select public.admin_pitch_video_decide('t901', 'approved', '{"problem": true, "solution": true, "market": true, "ask": false}')$q$, '22023');
select public.admin_pitch_video_decide('t901', 'approved', '{"problem": true, "solution": true, "market": true, "ask": true}');
select pg_temp.ok('M51 approving with all four checks records who approved it',
  (select status = 'approved' and decided_at is not null and decided_by_name = 'Ada Admin' from public.admin_pitch_videos() where video_id = 't901'));
select pg_temp.refused('M52 a reviewed video cannot be approved again',
  $q$select public.admin_pitch_video_decide('t901', 'approved', '{"problem": true, "solution": true, "market": true, "ask": true}')$q$, 'P0001');
select pg_temp.refused('M53 rejecting with a reason not on the list is refused',
  $q$select public.admin_pitch_video_decide('t902', 'rejected', null, 'I did not like it.')$q$, '22023');
select public.admin_pitch_video_decide('t902', 'rejected', null, 'The pitch does not name the ask.');
select pg_temp.ok('M54 rejecting with a reason on the list keeps the reason',
  (select status = 'rejected' and reason = 'The pitch does not name the ask.' from public.admin_pitch_videos() where video_id = 't902'));
select public.admin_pitch_video_reopen('t902');
select pg_temp.ok('M55 a reviewed video returns to pending review, without its reason',
  (select status = 'pending' and reason is null and decided_at is null from public.admin_pitch_videos() where video_id = 't902'));
select pg_temp.refused('M56 a pending video cannot be returned to pending', $q$select public.admin_pitch_video_reopen('t902')$q$, 'P0001');
reset role;
select pg_temp.ok('M57 each review is in the audit log',
  (select array_agg(action order by id) from public.audit_log where entity = 'pitch_video_files' and entity_id in ('t901', 't902'))
  = array['video.approve', 'video.reject', 'video.reopen']);
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M58 a reviewer cannot review a Drive video',
  $q$select public.admin_pitch_video_decide('t902', 'rejected', null, 'The pitch does not name the ask.')$q$, '42501');


-- ---------------------------------------------------------------- reports
reset role;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000012');
insert into public.introductions (venture_id, note) values
  ('ae000000-0000-0000-0000-00000000000f', 'I back payments companies and would like to hear how traders pay.');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000f');
update public.introductions set status = 'accepted' where venture_id = 'ae000000-0000-0000-0000-00000000000f';
create temp table convo as select id from public.introductions where venture_id = 'ae000000-0000-0000-0000-00000000000f';
grant select on convo to authenticated;
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000012');
select public.report_conversation((select id from convo), 'The founder sent messages that made me uncomfortable.');
reset role;
select pg_temp.ok('M60 the investor in a conversation reports it, and the report is about the founder',
  (select count(*) from public.reports where introduction_id = (select id from convo)
     and reporter_id = 'ad000000-0000-0000-0000-000000000012' and about_id = 'ad000000-0000-0000-0000-00000000000f'
     and status = 'open') = 1);
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000012');
select pg_temp.refused('M61 a second open report from the same person is refused',
  $q$select public.report_conversation((select id from convo), 'Another report about the same conversation.')$q$, 'P0001');
select pg_temp.refused('M62 a reason under ten characters is refused',
  $q$select public.report_conversation((select id from convo), 'Too short')$q$, '22023');
select pg_temp.as_user('ad000000-0000-0000-0000-000000000013');
select pg_temp.refused('M63 a person outside the conversation cannot report it',
  $q$select public.report_conversation((select id from convo), 'I was never part of this conversation.')$q$, 'P0002');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000f');
select public.report_conversation((select id from convo), 'The investor asked for my personal bank details.');
select pg_temp.refused('M64 a founder cannot read the reports', 'select * from public.admin_reports()', '42501');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.ok('M65 a reviewer reads the open reports with both names and the venture',
  (select array_agg(reporter_name || '>' || about_name || ':' || venture_name order by created_at, reporter_name)
   from public.admin_reports() where introduction_id = (select id from convo))
  = array['Iyke Investor>Fola Founder:Pilot Pay', 'Fola Founder>Iyke Investor:Pilot Pay']);
select pg_temp.refused('M66 a resolution under five characters is refused',
  $q$select public.admin_report_resolve((select id from public.admin_reports() where reporter_name = 'Fola Founder' limit 1), 'ok')$q$, '22023');
select public.admin_report_resolve((select id from public.admin_reports() where reporter_name = 'Fola Founder' and introduction_id = (select id from convo)),
  'Spoke to both people and reminded the investor of the rules.');
select pg_temp.ok('M67 a resolved report leaves the open list and stays in the full list',
  (select count(*) from public.admin_reports() where introduction_id = (select id from convo)) = 1
  and (select count(*) from public.admin_reports(true) where introduction_id = (select id from convo) and status = 'resolved') = 1);
select pg_temp.refused('M68 a resolved report cannot be resolved again',
  $q$select public.admin_report_resolve((select id from public.admin_reports(true) where status = 'resolved' and introduction_id = (select id from convo)), 'Again, with a note.')$q$, 'P0001');
reset role;
select pg_temp.ok('M69 resolving a report is in the audit log',
  (select count(*) from public.audit_log where action = 'report.resolve' and actor_id = 'ad000000-0000-0000-0000-00000000000c') = 1);
set role authenticated;

-- ---------------------------------------------------------------- settings and what they enforce
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M70 a reviewer cannot read the settings', 'select * from public.admin_settings()', '42501');
select pg_temp.refused('M70a a reviewer cannot change the settings',
  $q$select public.admin_set_platform_mode('maintenance', 'Back soon.')$q$, '42501');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M71 the settings start at the design''s values',
  (select pitch_types = '{video/mp4,video/webm,video/quicktime}' and pitch_max_mb = 50 and pitch_max_seconds = 90
      and introductions_on and introductions_per_day = 10 and mode = 'live'
      and maintenance_message = 'IkonetU is being updated and will be back shortly.'
   from public.admin_settings()));
select pg_temp.refused('M72 the pitch rules need a file type', $q$select public.admin_set_pitch_rules('{}', 20, 60)$q$, '22023');
select pg_temp.refused('M72a the pitch rules take MP4, WebM and MOV only',
  $q$select public.admin_set_pitch_rules('{video/avi}', 20, 60)$q$, '22023');
select pg_temp.refused('M72b the largest file is 1 to 50 MB', $q$select public.admin_set_pitch_rules('{video/mp4}', 51, 60)$q$, '22023');
select pg_temp.refused('M72c the longest pitch is 1 to 90 seconds', $q$select public.admin_set_pitch_rules('{video/mp4}', 20, 0)$q$, '22023');
select public.admin_set_pitch_rules('{video/quicktime,video/mp4,video/mp4}', 20, 60);
select pg_temp.ok('M73 the pitch rules are saved, each type once and in the usual order',
  (select pitch_types = '{video/mp4,video/quicktime}' and pitch_max_mb = 20 and pitch_max_seconds = 60 from public.admin_settings()));
reset role;
select pg_temp.refused('M74 the database refuses a pitch of a type the rules do not allow',
  $q$update public.pitches set storage_path = 'ad000000-0000-0000-0000-000000000010/p2.webm', mime_type = 'video/webm'
     where venture_id = 'ae000000-0000-0000-0000-000000000010'$q$, '22023');
select pg_temp.refused('M74a the database refuses a pitch over the largest file',
  $q$update public.pitches set storage_path = 'ad000000-0000-0000-0000-000000000010/p2.mp4', size_bytes = 20971521
     where venture_id = 'ae000000-0000-0000-0000-000000000010'$q$, '22023');
select pg_temp.refused('M74b the database refuses a pitch over the longest length',
  $q$update public.pitches set storage_path = 'ad000000-0000-0000-0000-000000000010/p2.mp4', duration_seconds = 61
     where venture_id = 'ae000000-0000-0000-0000-000000000010'$q$, '22023');
update public.pitches set storage_path = 'ad000000-0000-0000-0000-000000000010/p2.mp4', size_bytes = 20971520, duration_seconds = 60
 where venture_id = 'ae000000-0000-0000-0000-000000000010';
select pg_temp.ok('M75 a pitch inside the rules is accepted',
  (select storage_path from public.pitches where venture_id = 'ae000000-0000-0000-0000-000000000010') = 'ad000000-0000-0000-0000-000000000010/p2.mp4');
update public.pitches set transcript = 'We help market traders take payments by phone and by text.'
 where venture_id = 'ae000000-0000-0000-0000-00000000000f';
select pg_temp.ok('M75a a new transcript for a pitch added under the old rules is accepted',
  (select transcript like '%by text.' from public.pitches where venture_id = 'ae000000-0000-0000-0000-00000000000f'));
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.refused('M76 a daily limit under 1 is refused', $q$select public.admin_set_introduction_rules(true, 0)$q$, '22023');
select pg_temp.refused('M76a switching introductions on needs a daily limit', $q$select public.admin_set_introduction_rules(true, null)$q$, '22023');
select public.admin_set_introduction_rules(false, null);
select pg_temp.ok('M77 switching introductions off keeps the daily limit',
  (select not introductions_on and introductions_per_day = 10 from public.admin_settings()));
reset role;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000013');
select pg_temp.refused('M78 with introductions off, a request is refused',
  $q$insert into public.introductions (venture_id, note) values ('ae000000-0000-0000-0000-000000000010', 'I would like to hear more about the mill.')$q$, 'P0001');
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select public.admin_set_introduction_rules(true, 1);
reset role;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000012');
do $$
begin
  insert into public.introductions (venture_id, note) values ('ae000000-0000-0000-0000-000000000010', 'I would like to hear more about the mill.');
  perform pg_temp.ok('M79 with a limit of 1, a second request the same day is refused', false, 'insert succeeded');
exception when others then
  perform pg_temp.ok('M79 with a limit of 1, a second request the same day is refused', sqlerrm like '%limit of 1 requests a day%', sqlerrm);
end $$;
select pg_temp.as_user('ad000000-0000-0000-0000-000000000013');
insert into public.introductions (venture_id, note) values ('ae000000-0000-0000-0000-000000000010', 'I would like to hear more about the mill.');
select pg_temp.ok('M79a with a limit of 1, another investor''s first request is accepted',
  (select count(*) from public.introductions where investor_id = 'ad000000-0000-0000-0000-000000000013') = 1);
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.refused('M80 maintenance needs a message', $q$select public.admin_set_platform_mode('maintenance', '   ')$q$, '22023');
select public.admin_set_platform_mode('maintenance', '  Back at noon.  ');
reset role;
set role anon;
set request.jwt.claim.role = 'anon';
set request.jwt.claim.sub = '';
select pg_temp.ok('M81 a visitor reads the maintenance mode and its message',
  (select mode = 'maintenance' and maintenance_message = 'Back at noon.' and pitch_max_mb = 20 from public.platform_status()));
reset role;
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select public.admin_set_platform_mode('live', '');
select pg_temp.ok('M82 going live with no message keeps the last message',
  (select mode = 'live' and maintenance_message = 'Back at noon.' from public.admin_settings()));
reset role;
select pg_temp.ok('M83 each settings change is in the audit log',
  (select array_agg(action order by id) from public.audit_log where entity = 'platform_settings')
  = array['settings.pitch', 'settings.introductions', 'settings.introductions', 'settings.mode', 'settings.mode']);
select pg_temp.refused('M84 the settings row cannot be deleted', 'delete from public.platform_settings', 'P0001');
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
-- Back to the defaults, so a file run after this one finds them.
select public.admin_set_pitch_rules('{video/mp4,video/webm,video/quicktime}', 50, 90);
select public.admin_set_introduction_rules(true, 10);
select public.admin_set_platform_mode('live', 'IkonetU is being updated and will be back shortly.');

-- ---------------------------------------------------------------- staff
select pg_temp.ok('M90 the staff list holds the active admins and reviewers, admins first',
  (select array_agg(full_name) from public.admin_staff() where email like '%@records.test')
  = array['Ada Admin', 'Bola Admin', 'Rita Reviewer']);
select pg_temp.refused('M91 an email no account uses is refused', $q$select public.admin_staff_add('nobody@records.test', 'reviewer')$q$, 'P0002');
select pg_temp.refused('M92 staff are reviewers or admins', $q$select public.admin_staff_add('pam@records.test', 'founder')$q$, '22023');
select pg_temp.refused('M93 a person on the staff list already is refused', $q$select public.admin_staff_add('RITA@records.test', 'admin')$q$, 'P0001');
select pg_temp.refused('M93a a suspended account is refused', $q$select public.admin_staff_add('sade@records.test', 'admin')$q$, 'P0001');
select public.admin_staff_add('pam@records.test', 'reviewer');
select pg_temp.ok('M94 a person is added as a reviewer by their email address',
  exists (select 1 from public.admin_staff() where email = 'pam@records.test' and role = 'reviewer' and since > now() - interval '1 minute'));
insert into removed values ('pam', public.admin_staff_remove('ad000000-0000-0000-0000-000000000014'));
select pg_temp.ok('M95 a person with no venture taken off the staff list is suspended',
  (select result from removed where who = 'pam') = 'suspended'
  and not exists (select 1 from public.admin_staff() where email = 'pam@records.test'));
select public.admin_staff_add('fola@records.test', 'reviewer');
reset role;
select pg_temp.ok('M96 a founder made staff leaves investors'' view',
  (select published_at is null from public.ventures where id = 'ae000000-0000-0000-0000-00000000000f'));
set role authenticated;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
insert into removed values ('fola', public.admin_staff_remove('ad000000-0000-0000-0000-00000000000f'));
select pg_temp.ok('M97 a person with a venture taken off the staff list is a founder again',
  (select result from removed where who = 'fola') = 'founder'
  and (select role = 'founder' and status = 'active' from public.profiles where user_id = 'ad000000-0000-0000-0000-00000000000f'));
select pg_temp.refused('M98 nobody takes themselves off the staff list',
  $q$select public.admin_staff_remove('ad000000-0000-0000-0000-00000000000a')$q$, '42501');
select pg_temp.refused('M98a a person not on the staff list cannot be taken off it',
  $q$select public.admin_staff_remove('ad000000-0000-0000-0000-000000000013')$q$, 'P0002');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M99 a reviewer cannot add staff', $q$select public.admin_staff_add('jide@records.test', 'reviewer')$q$, '42501');

-- ---------------------------------------------------------------- the dashboard, analytics, audit and database
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M100 the dashboard counts the register founders and investors and leaves out the sample founder',
  (select (d ->> 'founders')::int = (select founders from base) + 2 and (d ->> 'investors')::int = (select investors from base) + 2
      and (d ->> 'sample')::boolean
   from public.admin_dashboard() d), (select public.admin_dashboard()::text));
select pg_temp.ok('M100a the sidebar counts the registers and says sample data is held',
  (select (s ->> 'founders')::int = (select founders from base) + 2 and (s ->> 'investors')::int = (select investors from base) + 2
      and (s ->> 'introductions')::int >= 3 and (s ->> 'sample')::boolean
   from public.admin_shell() s));
select pg_temp.ok('M101 the dashboard counts every introduction and message, the sample ones included',
  (select (d ->> 'intros')::int >= 3 and (d ->> 'intros_register')::int >= 2 and (d ->> 'messages')::int >= 5
      and (d ->> 'conversations')::int >= 1
   from public.admin_dashboard() d));
select pg_temp.ok('M102 the months run from January to this month, and January counts the founder who joined then',
  (select jsonb_array_length(d -> 'months') = extract(month from now() at time zone 'UTC')::int
      and (d -> 'months' -> 0 ->> 'month') = to_char(now() at time zone 'UTC', 'YYYY') || '-01'
   from public.admin_dashboard() d)
  and (extract(year from now()) <> 2026 or (select (d -> 'months' -> 0 ->> 'founders')::int >= 1 from public.admin_dashboard() d)));
select pg_temp.ok('M103 the support list keeps only a kind more than one founder named',
  (select d -> 'support' @> '[["Financial support", 2]]'::jsonb and not (d -> 'support' @> '[["Mentorship support", 1]]'::jsonb)
   from public.admin_dashboard() d));
select pg_temp.ok('M104 the analytics source leaves out the sample founder and holds no name',
  (select not (a -> 'founders' @> '[{"record_id": "s91"}]'::jsonb) and a -> 'founders' @> '[{"record_id": "p901"}]'::jsonb
      and a::text not like '%Name One%' and a::text not like '%one@register.test%'
   from public.admin_analytics_source() a));
select pg_temp.ok('M104a the analytics source gives each founder''s country by its grouped name, as the dashboard counts it',
  (select a -> 'founders' @> '[{"record_id": "p901", "country": "Ghana"}]'::jsonb
      and not (a -> 'founders' @> '[{"record_id": "p901", "country": "GHANA"}]'::jsonb)
   from public.admin_analytics_source() a));
select pg_temp.ok('M105 the register history marks the first response of each founder, with the name it was sent under',
  (select h -> 'responses' @> '[{"response_id": "f901", "first": true, "full_name": "Name One First"}, {"response_id": "f902", "first": false}]'::jsonb
      and not (h -> 'responses' @> '[{"record_id": "s91"}]'::jsonb)
      and h -> 'investors' @> '[{"register_no": "901"}]'::jsonb
   from public.admin_register_history() h));
select pg_temp.ok('M106 the database page lists every table with its rows and row security on',
  (select bool_and((t ->> 'rls')::boolean) and count(*) = (select count(*) from pg_tables where schemaname = 'public')
   from public.admin_database() d, jsonb_array_elements(d -> 'tables') t)
  and (select (t ->> 'rows')::int >= 2 and t -> 'columns' @> '["record_id", "joined_at"]'::jsonb
       from public.admin_database() d, jsonb_array_elements(d -> 'tables') t where t ->> 'name' = 'founder_register'));
reset role;
create schema supabase_migrations;
create table supabase_migrations.schema_migrations (version text primary key, name text);
insert into supabase_migrations.schema_migrations values ('20261024000001', 'investor_register'), ('20261027000002', 'admin_records');
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M106a the database page counts the migrations Supabase recorded and names the latest',
  (select d -> 'migrations' = '{"count": 2, "latest": "20261027000002", "name": "admin_records"}'::jsonb
   from public.admin_database() d));
reset role;
drop schema supabase_migrations cascade;
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000a');
select pg_temp.ok('M105a a limit keeps the newest response and the newest register entry',
  (select jsonb_array_length(h -> 'responses') = 1 and jsonb_array_length(h -> 'investors') = 1
   from public.admin_register_history(1) h));
select pg_temp.as_user('ad000000-0000-0000-0000-00000000000c');
select pg_temp.refused('M107b a reviewer cannot read the sidebar counts', 'select public.admin_shell()', '42501');
select pg_temp.refused('M107 a reviewer cannot see the database page', 'select public.admin_database()', '42501');
select pg_temp.refused('M107a a reviewer cannot read the register history', 'select public.admin_register_history()', '42501');

reset role;
select pg_temp.ok('M108 every new table has row security on and gives anon and authenticated no right',
  (select bool_and(c.relrowsecurity
       and not has_table_privilege('anon', c.oid, 'select, insert, update, delete')
       and not has_table_privilege('authenticated', c.oid, 'select, insert, update, delete'))
   from pg_class c join pg_namespace s on s.oid = c.relnamespace
   where s.nspname = 'public' and c.relname in ('founder_register', 'founder_register_responses', 'register_imports',
     'register_introductions', 'pitch_video_files', 'reports', 'platform_settings')));
select pg_temp.ok('M109 a visitor can call no admin function',
  not exists (select 1 from pg_proc p join pg_namespace s on s.oid = p.pronamespace
              where s.nspname = 'public' and p.proname like 'admin\_%' and has_function_privilege('anon', p.oid, 'execute')));
