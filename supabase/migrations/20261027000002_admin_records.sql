-- ---------------------------------------------------------------------------
-- The admin records. Written 27 October 2026.
--
-- On 26 October 2026 the owner approved the admin redesign and asked for it to
-- be built into the app "with all the data migrated alongside". The design
-- holds records that no table held: the founders who answered the register
-- form, their answers, introductions made by IkonetU between the two
-- registers, and the pitch videos sent to IkonetU's Google Drive. This
-- migration adds the tables for them, the platform settings, and the functions
-- the admin pages read and change them through.
--
-- 1. founder_register holds one founder from the register form, with
--    founder_register_responses holding each time the form was sent. A
--    founder who sent it twice has one record and two responses, as the
--    design groups them. register_imports records each load of the form's
--    answers, with how many responses arrived and how many were removed as
--    tests.
-- 2. investor_register gains a link to an investor's IkonetU account, made by
--    an admin who gives the account's email address.
-- 3. register_introductions holds an introduction IkonetU made between a
--    register investor and a register founder, with its status and the count
--    of messages the design records. Staff see the count only.
-- 4. pitch_video_files holds a pitch video kept in Google Drive, with its
--    review. Approving one needs all four checks ticked, and rejecting one
--    needs one of six reasons.
-- 5. reports holds a report a founder or an investor makes about a
--    conversation, for staff to resolve.
-- 6. platform_settings holds the pitch rules, the introduction rules and the
--    platform mode in one row. The database enforces the pitch rules on every
--    pitch and the introduction rules on every request. The app enforces the
--    mode, because a sign-in is not a database write.
-- 7. Rows marked sample are the design's sample data: four founders, one
--    investor and four accepted introductions. They are not on either
--    register, so the register counts leave them out, and the admin pages
--    label them.
--
-- Every new table has row level security on and no policy, so nobody reads or
-- writes one directly. The admin functions check the caller's role and write
-- the audit log. The register data is personal data, so none of it is in this
-- file or anywhere else in the repository.
--
-- As written on 27 October 2026, this migration has been applied to a local
-- PostgreSQL 16 only, where supabase/tests/08_admin_records_checks.sql
-- passed. It needs 20261027000001_activity_feed.sql first.
-- ---------------------------------------------------------------------------

create type public.register_intro_status as enum ('pending', 'accepted', 'declined', 'withdrawn');
create type public.video_review_status as enum ('pending', 'approved', 'rejected');
create type public.report_status as enum ('open', 'resolved');
create type public.platform_mode as enum ('live', 'maintenance');

-- ---------------------------------------------------------------- 1. founders on the register
create table public.founder_register (
  record_id text primary key check (record_id ~ '^(p[0-9]{3,6}|s[0-9]{2,6})$'),
  sample boolean not null default false,
  full_name text not null default '' check (char_length(full_name) <= 200),
  email text not null default '' check (char_length(email) <= 320),
  phone text not null default '' check (char_length(phone) <= 40),
  country text not null default '' check (char_length(country) <= 100),
  -- The country as the pages group it: title case, with "Nigerian" read as Nigeria.
  country_key text not null check (char_length(country_key) between 1 and 100),
  university text not null default '' check (char_length(university) <= 300),
  startup text not null default '' check (char_length(startup) <= 300),
  sector text not null default '' check (char_length(sector) <= 300),
  stage text not null default '' check (char_length(stage) <= 1000),
  amount text not null default '' check (char_length(amount) <= 1000),
  study_year text not null default '' check (char_length(study_year) <= 200),
  degree text not null default '' check (char_length(degree) <= 300),
  problem text not null default '' check (char_length(problem) <= 4000),
  target_market text not null default '' check (char_length(target_market) <= 4000),
  unique_answer text not null default '' check (char_length(unique_answer) <= 4000),
  support text[] not null default '{}' check (cardinality(support) <= 20),
  joined_at timestamptz not null,
  last_response_at timestamptz not null,
  loaded_at timestamptz not null default now(),
  check (sample = (record_id like 's%')),
  check (last_response_at >= joined_at)
);
alter table public.founder_register enable row level security;
revoke all on public.founder_register from anon, authenticated;

-- Each response keeps what it said, so the audit log shows a founder's earlier
-- answers as they were sent. The record holds the latest.
create table public.founder_register_responses (
  response_id text primary key check (response_id ~ '^f[0-9]{3,6}$'),
  record_id text not null references public.founder_register (record_id) on delete cascade,
  responded_at timestamptz not null,
  full_name text not null default '' check (char_length(full_name) <= 200),
  email text not null default '' check (char_length(email) <= 320),
  phone text not null default '' check (char_length(phone) <= 40),
  country text not null default '' check (char_length(country) <= 100),
  university text not null default '' check (char_length(university) <= 300),
  startup text not null default '' check (char_length(startup) <= 300),
  sector text not null default '' check (char_length(sector) <= 300)
);
create index founder_register_responses_record on public.founder_register_responses (record_id, responded_at);
alter table public.founder_register_responses enable row level security;
revoke all on public.founder_register_responses from anon, authenticated;

create table public.register_imports (
  id bigint generated always as identity primary key,
  source text not null check (char_length(source) between 3 and 200),
  responses_received integer not null check (responses_received >= 0),
  removed_as_test integer not null default 0 check (removed_as_test >= 0),
  responses_kept integer not null check (responses_kept >= 0),
  founders integer not null check (founders >= 0),
  loaded_at timestamptz not null default now(),
  check (responses_kept = responses_received - removed_as_test)
);
alter table public.register_imports enable row level security;
revoke all on public.register_imports from anon, authenticated;

-- ---------------------------------------------------------------- 2. the investor register's account link
alter table public.investor_register
  add column account_id uuid unique references auth.users (id) on delete set null,
  add column linked_at timestamptz,
  add column linked_by uuid references auth.users (id),
  add constraint investor_register_link_dated check (account_id is null or linked_at is not null);

-- ---------------------------------------------------------------- 3. introductions between the registers
-- A sample introduction names its investor here, because the sample investor
-- is not on the register. Every other introduction names a register number.
create table public.register_introductions (
  intro_id text primary key check (intro_id ~ '^[ns][0-9]{3,6}$'),
  sample boolean not null default false,
  investor_no text references public.investor_register (register_no),
  investor_name text check (investor_name is null or char_length(investor_name) between 2 and 120),
  investor_registered_on date,
  record_id text not null references public.founder_register (record_id) on delete cascade,
  made_on date not null,
  status public.register_intro_status not null default 'pending',
  note text not null default '' check (char_length(note) <= 1000),
  messages integer not null default 0 check (messages >= 0),
  accepted_on date,
  changed_at timestamptz,
  changed_by uuid references auth.users (id),
  check (sample = (intro_id like 's%')),
  check ((sample and investor_no is null and investor_name is not null and investor_registered_on is not null)
      or (not sample and investor_no is not null and investor_name is null and investor_registered_on is null)),
  check (accepted_on is null or accepted_on >= made_on)
);
create index register_introductions_record on public.register_introductions (record_id);
create index register_introductions_investor on public.register_introductions (investor_no);
alter table public.register_introductions enable row level security;
revoke all on public.register_introductions from anon, authenticated;

-- A sample introduction joins a sample founder, and a register introduction a register founder.
create or replace function public.guard_register_introduction() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select f.sample from public.founder_register f where f.record_id = new.record_id) is distinct from new.sample then
    raise exception 'a sample introduction joins a sample founder, and a register introduction a register founder'
      using errcode = '23514';
  end if;
  return new;
end;
$$;
create trigger register_introductions_guard before insert or update of record_id, sample on public.register_introductions
  for each row execute function public.guard_register_introduction();

-- ---------------------------------------------------------------- 4. pitch videos in Google Drive
create table public.pitch_video_files (
  video_id text primary key check (video_id ~ '^t[0-9]{2,6}$'),
  file_name text not null check (char_length(file_name) between 1 and 300),
  file_type text not null check (file_type ~ '^[A-Z0-9]{2,5}$'),
  -- The size as Google Drive gave it, such as 47.9 MB or 136 KB.
  size_text text not null check (size_text ~ '^[0-9]+(\.[0-9]+)? (KB|MB|GB)$'),
  folder text not null check (char_length(folder) between 1 and 200),
  added_on date not null,
  drive_url text not null unique check (drive_url ~ '^https://drive\.google\.com/file/d/[A-Za-z0-9_-]+/view$'),
  transcript text check (transcript is null or char_length(transcript) between 1 and 5000),
  -- The founder record the video belongs to, when an admin knows it. None is known yet.
  record_id text references public.founder_register (record_id) on delete set null,
  status public.video_review_status not null default 'pending',
  checks jsonb,
  reason text,
  decided_at timestamptz,
  decided_by uuid references auth.users (id),
  check ((status = 'pending') = (decided_at is null)),
  check ((status = 'rejected') = (reason is not null)),
  check ((status = 'approved') = (checks is not null)),
  check (checks is null or checks = '{"problem": true, "solution": true, "market": true, "ask": true}'::jsonb)
);
alter table public.pitch_video_files enable row level security;
revoke all on public.pitch_video_files from anon, authenticated;

-- ---------------------------------------------------------------- 5. reports about conversations
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  introduction_id uuid not null references public.introductions (id) on delete cascade,
  reporter_id uuid not null references auth.users (id) on delete cascade,
  about_id uuid not null references auth.users (id) on delete cascade,
  reason text not null check (char_length(reason) between 10 and 2000),
  status public.report_status not null default 'open',
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  resolved_by uuid references auth.users (id),
  resolution text check (resolution is null or char_length(resolution) between 5 and 280),
  check ((status = 'resolved') = (resolved_at is not null)),
  check (reporter_id <> about_id)
);
-- One open report from each person about each conversation.
create unique index reports_one_open on public.reports (introduction_id, reporter_id) where status = 'open';
alter table public.reports enable row level security;
revoke all on public.reports from anon, authenticated;

-- ---------------------------------------------------------------- 6. platform settings
create table public.platform_settings (
  id boolean primary key default true check (id),
  pitch_types text[] not null default '{video/mp4,video/webm,video/quicktime}'
    check (cardinality(pitch_types) between 1 and 3 and pitch_types <@ '{video/mp4,video/webm,video/quicktime}'::text[]),
  pitch_max_mb integer not null default 50 check (pitch_max_mb between 1 and 50),
  pitch_max_seconds integer not null default 90 check (pitch_max_seconds between 1 and 90),
  introductions_on boolean not null default true,
  introductions_per_day integer not null default 10 check (introductions_per_day >= 1),
  mode public.platform_mode not null default 'live',
  maintenance_message text not null default 'IkonetU is being updated and will be back shortly.'
    check (char_length(maintenance_message) between 1 and 280 and maintenance_message = btrim(maintenance_message)),
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users (id)
);
insert into public.platform_settings default values;
alter table public.platform_settings enable row level security;
revoke all on public.platform_settings from anon, authenticated;
create trigger platform_settings_kept before delete on public.platform_settings
  for each row execute function public.forbid_change();

-- What everyone may know: the mode and its message, and the rules a founder or
-- an investor is held to. Nothing in it is private.
create or replace function public.platform_status()
returns table (
  mode public.platform_mode, maintenance_message text, pitch_types text[], pitch_max_mb integer,
  pitch_max_seconds integer, introductions_on boolean, introductions_per_day integer
)
language sql stable security definer set search_path = public as $$
  select s.mode, s.maintenance_message, s.pitch_types, s.pitch_max_mb, s.pitch_max_seconds,
    s.introductions_on, s.introductions_per_day
  from public.platform_settings s;
$$;

-- The introduction rules, enforced where every request is written. The rest of
-- the function is as migration 20261015000004 left it.
create or replace function public.prepare_introduction() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v public.ventures;
  inv public.profiles;
  ip public.investor_profiles;
  f public.profiles;
  rules public.platform_settings;
begin
  select * into v from public.ventures where id = new.venture_id;
  if not found or v.published_at is null then
    raise exception 'this founder profile is not published' using errcode = 'P0001';
  end if;
  select * into inv from public.profiles where user_id = auth.uid() and role = 'investor' and status = 'active';
  select * into ip from public.investor_profiles where user_id = auth.uid();
  if inv.user_id is null or ip.user_id is null then
    raise exception 'only approved investors can request introductions' using errcode = '42501';
  end if;
  select * into rules from public.platform_settings;
  if not rules.introductions_on then
    raise exception 'introduction requests are switched off' using errcode = 'P0001';
  end if;
  -- A daily limit per investor, so no founder is flooded by one person. The
  -- lock makes a second simultaneous request from the same investor wait
  -- until the first commits, so its count includes the first.
  perform pg_advisory_xact_lock(hashtextextended('introductions:' || auth.uid()::text, 0));
  if (select count(*) from public.introductions
      where investor_id = auth.uid() and created_at > now() - interval '1 day') >= rules.introductions_per_day then
    raise exception 'you have reached the limit of % requests a day', rules.introductions_per_day using errcode = 'P0001';
  end if;
  select * into f from public.profiles where user_id = v.founder_id;
  new.investor_id := auth.uid();
  new.founder_id := v.founder_id;
  new.status := 'pending';
  new.decided_at := null;
  new.created_at := now();
  new.investor_name := inv.full_name;
  new.investor_type := ip.investor_type;
  new.investor_firm := ip.firm;
  new.venture_name := v.name;
  new.founder_name := f.full_name;
  return new;
end;
$$;

-- The pitch rules, checked when a video is added or replaced. A change to the
-- transcript alone is not held to rules made after the video was added.
create or replace function public.guard_pitch_rules() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  rules public.platform_settings;
begin
  if tg_op = 'UPDATE' and new.storage_path = old.storage_path and new.mime_type = old.mime_type
     and new.size_bytes = old.size_bytes and new.duration_seconds = old.duration_seconds then
    return new;
  end if;
  select * into rules from public.platform_settings;
  if not new.mime_type = any (rules.pitch_types) then
    raise exception 'this type of video is not accepted for pitches' using errcode = '22023';
  end if;
  if new.size_bytes > rules.pitch_max_mb * 1048576 then
    raise exception 'the pitch video is larger than % MB', rules.pitch_max_mb using errcode = '22023';
  end if;
  if new.duration_seconds > rules.pitch_max_seconds then
    raise exception 'the pitch is longer than % seconds', rules.pitch_max_seconds using errcode = '22023';
  end if;
  return new;
end;
$$;
create trigger pitches_rules before insert or update on public.pitches
  for each row execute function public.guard_pitch_rules();

-- ---------------------------------------------------------------- 7. reading the registers
-- Every founder on the register, without the sample founders. The long
-- answers come only with p_full, for the CSV export.
create or replace function public.admin_founder_records(p_full boolean default false)
returns table (
  record_id text, full_name text, email text, phone text, country text, country_key text, university text,
  startup text, sector text, stage text, amount text, study_year text, degree text, problem text,
  target_market text, unique_answer text, support text[], joined_at timestamptz, last_response_at timestamptz,
  responses integer, video_status text
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the founder register' using errcode = '42501';
  end if;
  return query
  select r.record_id, r.full_name, r.email, r.phone, r.country, r.country_key, r.university, r.startup, r.sector,
    r.stage,
    case when p_full then r.amount end, case when p_full then r.study_year end, case when p_full then r.degree end,
    case when p_full then r.problem end, case when p_full then r.target_market end,
    case when p_full then r.unique_answer end,
    r.support, r.joined_at, r.last_response_at,
    (select count(*)::integer from public.founder_register_responses w where w.record_id = r.record_id),
    coalesce((select v.status::text from public.pitch_video_files v where v.record_id = r.record_id
              order by v.added_on desc, v.video_id desc limit 1), 'none')
  from public.founder_register r
  where not r.sample
  order by r.joined_at, r.record_id;
end;
$$;

-- One founder record, sample or not, with its responses, its introductions and
-- its pitch video. Null when there is no such record.
create or replace function public.admin_founder_record(p_id text)
returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare
  r public.founder_register;
begin
  if not public.is_admin() then
    raise exception 'only admins can read the founder register' using errcode = '42501';
  end if;
  select * into r from public.founder_register where record_id = p_id;
  if not found then
    return null;
  end if;
  return to_jsonb(r) || jsonb_build_object(
    'responses', coalesce((select jsonb_agg(jsonb_build_object(
        'response_id', w.response_id, 'responded_at', w.responded_at, 'startup', w.startup, 'sector', w.sector)
        order by w.responded_at, w.response_id)
      from public.founder_register_responses w where w.record_id = r.record_id), '[]'::jsonb),
    'introductions', coalesce((select jsonb_agg(jsonb_build_object(
        'intro_id', i.intro_id, 'investor_no', i.investor_no,
        'investor_name', coalesce(g.full_name, i.investor_name), 'made_on', i.made_on, 'status', i.status,
        'messages', i.messages, 'accepted_on', i.accepted_on, 'sample', i.sample)
        order by i.made_on, i.intro_id)
      from public.register_introductions i left join public.investor_register g on g.register_no = i.investor_no
      where i.record_id = r.record_id), '[]'::jsonb),
    'video', (select jsonb_build_object('video_id', v.video_id, 'file_name', v.file_name, 'status', v.status)
      from public.pitch_video_files v where v.record_id = r.record_id order by v.added_on desc, v.video_id desc limit 1)
  );
end;
$$;

-- Deletes a founder record with its responses and its introductions. The audit
-- log keeps the record number and the counts, and none of the personal data.
create or replace function public.admin_founder_record_delete(p_id text) returns void
language plpgsql security definer set search_path = public as $$
declare
  n_responses integer;
  n_intros integer;
  was_sample boolean;
begin
  if not public.is_admin() then
    raise exception 'only admins can delete a founder record' using errcode = '42501';
  end if;
  select f.sample into was_sample from public.founder_register f where f.record_id = p_id for update;
  if not found then
    raise exception 'record not found' using errcode = 'P0002';
  end if;
  select count(*) into n_responses from public.founder_register_responses where record_id = p_id;
  select count(*) into n_intros from public.register_introductions where record_id = p_id;
  delete from public.founder_register where record_id = p_id;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'register.founder_delete', 'founder_register', p_id,
          jsonb_build_object('responses', n_responses, 'introductions', n_intros, 'sample', was_sample), null);
end;
$$;

-- People who signed in but never chose to be a founder or an investor. The
-- email address and the dates come from Supabase Auth.
create or replace function public.admin_unfinished_signups()
returns table (user_id uuid, email text, started_at timestamptz, email_confirmed boolean)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read sign-ups' using errcode = '42501';
  end if;
  return query
  select u.id, u.email::text, u.created_at, u.email_confirmed_at is not null
  from auth.users u
  where not exists (select 1 from public.profiles p where p.user_id = u.id)
  order by u.created_at desc, u.id;
end;
$$;

-- Removes a sign-up that never chose a role, and with it the Supabase Auth
-- account. An account with a profile cannot be removed here.
create or replace function public.admin_remove_signup(p_user uuid) returns void
language plpgsql security definer set search_path = public as $$
declare
  confirmed boolean;
begin
  if not public.is_admin() then
    raise exception 'only admins can remove a sign-up' using errcode = '42501';
  end if;
  if p_user = auth.uid() then
    raise exception 'nobody can remove their own account here' using errcode = '42501';
  end if;
  if exists (select 1 from public.profiles where user_id = p_user) then
    raise exception 'this person has chosen a role, so the sign-up is finished' using errcode = 'P0001';
  end if;
  select u.email_confirmed_at is not null into confirmed from auth.users u where u.id = p_user for update;
  if not found then
    raise exception 'sign-up not found' using errcode = 'P0002';
  end if;
  delete from auth.users where id = p_user;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'account.remove_signup', 'auth.users', p_user::text,
          jsonb_build_object('email_confirmed', confirmed), null);
end;
$$;

-- ---------------------------------------------------------------- 8. the investor register, with accounts
drop function public.admin_register(text, date, integer, integer);
-- Every entry in register number order, with its linked account and the
-- introductions made from it. p_month, any day of a month, keeps the entries
-- registered in that month. p_account takes 'any', 'linked' or 'not'.
create or replace function public.admin_register(
  p_search text default null, p_month date default null, p_limit integer default 50, p_offset integer default 0,
  p_account text default 'any'
)
returns table (
  register_no text, full_name text, registered_on date, added_at timestamptz,
  account_id uuid, account_name text, account_email text, linked_at timestamptz, introductions integer,
  total_count bigint
)
language plpgsql stable security definer set search_path = public as $$
declare
  q text := nullif(btrim(coalesce(p_search, '')), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can read the investor register' using errcode = '42501';
  end if;
  return query
  select r.register_no, r.full_name, r.registered_on, r.added_at, r.account_id, p.full_name, u.email::text,
    r.linked_at,
    (select count(*)::integer from public.register_introductions i where i.investor_no = r.register_no),
    count(*) over ()
  from public.investor_register r
  left join public.profiles p on p.user_id = r.account_id
  left join auth.users u on u.id = r.account_id
  where (q is null or r.full_name ilike '%' || q || '%' or strpos(r.register_no, q) > 0)
    and (p_month is null or date_trunc('month', r.registered_on) = date_trunc('month', p_month))
    and case coalesce(p_account, 'any')
          when 'linked' then r.account_id is not null
          when 'not' then r.account_id is null
          else true
        end
  order by char_length(r.register_no), r.register_no
  limit least(greatest(coalesce(p_limit, 50), 1), 1000)
  offset greatest(coalesce(p_offset, 0), 0);
end;
$$;

-- Links a register entry to the investor account that uses an email address.
create or replace function public.admin_register_link(p_no text, p_email text) returns void
language plpgsql security definer set search_path = public as $$
declare
  entry public.investor_register;
  account uuid;
  other text;
begin
  if not public.is_admin() then
    raise exception 'only admins can link the investor register' using errcode = '42501';
  end if;
  select * into entry from public.investor_register where register_no = p_no for update;
  if not found then
    raise exception 'register entry not found' using errcode = 'P0002';
  end if;
  if entry.account_id is not null then
    raise exception 'this register entry is already linked to an account' using errcode = 'P0001';
  end if;
  select u.id into account
  from auth.users u join public.profiles p on p.user_id = u.id and p.role = 'investor'
  where lower(u.email::text) = lower(btrim(coalesce(p_email, '')));
  if account is null then
    raise exception 'no investor account uses this email address' using errcode = 'P0002';
  end if;
  select r.register_no into other from public.investor_register r where r.account_id = account;
  if other is not null then
    raise exception 'this account is already linked to register entry %', other using errcode = 'P0001';
  end if;
  update public.investor_register set account_id = account, linked_at = now(), linked_by = auth.uid()
  where register_no = p_no;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'register.link', 'investor_register', p_no, jsonb_build_object('account_id', null),
          jsonb_build_object('account_id', account));
end;
$$;

create or replace function public.admin_register_unlink(p_no text) returns void
language plpgsql security definer set search_path = public as $$
declare
  entry public.investor_register;
begin
  if not public.is_admin() then
    raise exception 'only admins can link the investor register' using errcode = '42501';
  end if;
  select * into entry from public.investor_register where register_no = p_no for update;
  if not found then
    raise exception 'register entry not found' using errcode = 'P0002';
  end if;
  if entry.account_id is null then
    raise exception 'this register entry is not linked to an account' using errcode = 'P0001';
  end if;
  update public.investor_register set account_id = null, linked_at = null, linked_by = null where register_no = p_no;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'register.unlink', 'investor_register', p_no, jsonb_build_object('account_id', entry.account_id),
          jsonb_build_object('account_id', null));
end;
$$;

-- ---------------------------------------------------------------- 9. introductions between the registers
create or replace function public.admin_register_introductions(p_id text default null)
returns table (
  intro_id text, sample boolean, investor_no text, investor_name text, investor_registered_on date,
  record_id text, founder_name text, founder_email text, founder_phone text, startup text, sector text,
  country_key text, founder_joined_at timestamptz, founder_sample boolean,
  made_on date, status public.register_intro_status, note text, messages integer, accepted_on date,
  changed_at timestamptz
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read introductions' using errcode = '42501';
  end if;
  return query
  select i.intro_id, i.sample, i.investor_no, coalesce(g.full_name, i.investor_name),
    coalesce(g.registered_on, i.investor_registered_on),
    f.record_id, f.full_name, f.email, f.phone, f.startup, f.sector, f.country_key, f.joined_at, f.sample,
    i.made_on, i.status, i.note, i.messages, i.accepted_on, i.changed_at
  from public.register_introductions i
  join public.founder_register f on f.record_id = i.record_id
  left join public.investor_register g on g.register_no = i.investor_no
  where p_id is null or i.intro_id = p_id
  order by i.intro_id;
end;
$$;

-- A pending introduction is marked accepted, declined or withdrawn, and any
-- other is returned to pending. Each change is written to the audit log, which
-- is the introduction's history.
create or replace function public.admin_register_introduction_status(p_id text, p_status public.register_intro_status)
returns void
language plpgsql security definer set search_path = public as $$
declare
  was public.register_intro_status;
begin
  if not public.is_admin() then
    raise exception 'only admins can change an introduction' using errcode = '42501';
  end if;
  select i.status into was from public.register_introductions i where i.intro_id = p_id for update;
  if not found then
    raise exception 'introduction not found' using errcode = 'P0002';
  end if;
  if (was = 'pending') = (p_status = 'pending') then
    raise exception 'a pending introduction is accepted, declined or withdrawn, and any other returns to pending'
      using errcode = 'P0001';
  end if;
  update public.register_introductions set status = p_status, changed_at = now(), changed_by = auth.uid()
  where intro_id = p_id;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'introduction.status', 'register_introductions', p_id,
          jsonb_build_object('status', was), jsonb_build_object('status', p_status));
end;
$$;

-- ---------------------------------------------------------------- 10. pitch videos in Google Drive
-- A video linked to a founder record carries that record's startup, founder and sector, as the Videos board
-- titled each card.
create or replace function public.admin_pitch_videos()
returns table (
  video_id text, file_name text, file_type text, size_text text, folder text, added_on date, drive_url text,
  transcript text, record_id text, status public.video_review_status, reason text, decided_at timestamptz,
  decided_by_name text, startup text, founder_name text, sector text
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the pitch videos' using errcode = '42501';
  end if;
  return query
  select v.video_id, v.file_name, v.file_type, v.size_text, v.folder, v.added_on, v.drive_url, v.transcript,
    v.record_id, v.status, v.reason, v.decided_at, p.full_name, f.startup, f.full_name, f.sector
  from public.pitch_video_files v
  left join public.profiles p on p.user_id = v.decided_by
  left join public.founder_register f on f.record_id = v.record_id
  order by v.video_id;
end;
$$;

-- Approving needs all four checks, and rejecting needs one of the six reasons.
create or replace function public.admin_pitch_video_decide(
  p_id text, p_decision public.video_review_status, p_checks jsonb default null, p_reason text default null
)
returns void
language plpgsql security definer set search_path = public as $$
declare
  was public.video_review_status;
begin
  if not public.is_admin() then
    raise exception 'only admins can review a pitch video' using errcode = '42501';
  end if;
  select v.status into was from public.pitch_video_files v where v.video_id = p_id for update;
  if not found then
    raise exception 'video not found' using errcode = 'P0002';
  end if;
  if was <> 'pending' then
    raise exception 'this video has been reviewed already' using errcode = 'P0001';
  end if;
  if p_decision = 'approved' then
    if p_checks is distinct from '{"problem": true, "solution": true, "market": true, "ask": true}'::jsonb then
      raise exception 'tick all four checks to approve' using errcode = '22023';
    end if;
    update public.pitch_video_files
       set status = 'approved', checks = p_checks, reason = null, decided_at = now(), decided_by = auth.uid()
     where video_id = p_id;
  elsif p_decision = 'rejected' then
    if p_reason is null or p_reason not in (
      'The pitch does not name the problem.', 'The pitch does not name the solution.',
      'The pitch does not name the market.', 'The pitch does not name the ask.',
      'The sound or the picture is not clear enough.', 'The video breaks the platform rules.') then
      raise exception 'choose one of the reasons' using errcode = '22023';
    end if;
    update public.pitch_video_files
       set status = 'rejected', checks = null, reason = p_reason, decided_at = now(), decided_by = auth.uid()
     where video_id = p_id;
  else
    raise exception 'approve or reject the video' using errcode = '22023';
  end if;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), case when p_decision = 'approved' then 'video.approve' else 'video.reject' end,
          'pitch_video_files', p_id, jsonb_build_object('status', was),
          jsonb_build_object('status', p_decision, 'reason', case when p_decision = 'rejected' then p_reason end));
end;
$$;

create or replace function public.admin_pitch_video_reopen(p_id text) returns void
language plpgsql security definer set search_path = public as $$
declare
  was public.video_review_status;
begin
  if not public.is_admin() then
    raise exception 'only admins can review a pitch video' using errcode = '42501';
  end if;
  select v.status into was from public.pitch_video_files v where v.video_id = p_id for update;
  if not found then
    raise exception 'video not found' using errcode = 'P0002';
  end if;
  if was = 'pending' then
    raise exception 'this video is waiting for review already' using errcode = 'P0001';
  end if;
  update public.pitch_video_files
     set status = 'pending', checks = null, reason = null, decided_at = null, decided_by = null
   where video_id = p_id;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'video.reopen', 'pitch_video_files', p_id, jsonb_build_object('status', was),
          jsonb_build_object('status', 'pending'));
end;
$$;

-- ---------------------------------------------------------------- 11. reports
-- A founder or an investor reports a conversation they are part of. The report
-- is about the other person in it.
create or replace function public.report_conversation(p_introduction uuid, p_reason text) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  i public.introductions;
  reason text := btrim(coalesce(p_reason, ''));
  made uuid;
begin
  select * into i from public.introductions where id = p_introduction;
  if not found or auth.uid() is null or auth.uid() not in (i.founder_id, i.investor_id) then
    raise exception 'conversation not found' using errcode = 'P0002';
  end if;
  if char_length(reason) not between 10 and 2000 then
    raise exception 'say what happened in 10 to 2,000 characters' using errcode = '22023';
  end if;
  if exists (select 1 from public.reports r where r.introduction_id = i.id and r.reporter_id = auth.uid() and r.status = 'open') then
    raise exception 'you have reported this conversation already' using errcode = 'P0001';
  end if;
  insert into public.reports (introduction_id, reporter_id, about_id, reason)
  values (i.id, auth.uid(), case when auth.uid() = i.founder_id then i.investor_id else i.founder_id end, reason)
  returning id into made;
  return made;
end;
$$;

-- Open reports for staff, oldest first, or every report with p_all.
create or replace function public.admin_reports(p_all boolean default false)
returns table (
  id uuid, introduction_id uuid, venture_name text, reporter_id uuid, reporter_name text, reporter_role public.user_role,
  about_id uuid, about_name text, reason text, status public.report_status, created_at timestamptz,
  resolved_at timestamptz, resolution text
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can read reports' using errcode = '42501';
  end if;
  return query
  select r.id, r.introduction_id, i.venture_name, r.reporter_id, rp.full_name, rp.role, r.about_id, ap.full_name,
    r.reason, r.status, r.created_at, r.resolved_at, r.resolution
  from public.reports r
  join public.introductions i on i.id = r.introduction_id
  left join public.profiles rp on rp.user_id = r.reporter_id
  left join public.profiles ap on ap.user_id = r.about_id
  where p_all or r.status = 'open'
  order by r.created_at, r.id;
end;
$$;

create or replace function public.admin_report_resolve(p_id uuid, p_note text) returns void
language plpgsql security definer set search_path = public as $$
declare
  note text := btrim(coalesce(p_note, ''));
  was public.report_status;
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can resolve a report' using errcode = '42501';
  end if;
  if char_length(note) not between 5 and 280 then
    raise exception 'say what was done in 5 to 280 characters' using errcode = '22023';
  end if;
  select r.status into was from public.reports r where r.id = p_id for update;
  if not found then
    raise exception 'report not found' using errcode = 'P0002';
  end if;
  if was = 'resolved' then
    raise exception 'this report is resolved already' using errcode = 'P0001';
  end if;
  update public.reports set status = 'resolved', resolved_at = now(), resolved_by = auth.uid(), resolution = note
  where id = p_id;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'report.resolve', 'reports', p_id::text, jsonb_build_object('status', was),
          jsonb_build_object('status', 'resolved', 'note', note));
end;
$$;

-- ---------------------------------------------------------------- 12. settings
create or replace function public.admin_settings()
returns table (
  pitch_types text[], pitch_max_mb integer, pitch_max_seconds integer, introductions_on boolean,
  introductions_per_day integer, mode public.platform_mode, maintenance_message text, updated_at timestamptz
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the settings' using errcode = '42501';
  end if;
  return query
  select s.pitch_types, s.pitch_max_mb, s.pitch_max_seconds, s.introductions_on, s.introductions_per_day, s.mode,
    s.maintenance_message, s.updated_at
  from public.platform_settings s;
end;
$$;

create or replace function public.admin_set_pitch_rules(p_types text[], p_max_mb integer, p_max_seconds integer)
returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.platform_settings;
  types text[];
begin
  if not public.is_admin() then
    raise exception 'only admins can change the settings' using errcode = '42501';
  end if;
  select array_agg(t order by array_position('{video/mp4,video/webm,video/quicktime}'::text[], t)) into types
  from (select distinct unnest(coalesce(p_types, '{}')) as t) x;
  if types is null then
    raise exception 'allow at least one file type' using errcode = '22023';
  end if;
  if not types <@ '{video/mp4,video/webm,video/quicktime}'::text[] then
    raise exception 'allow MP4, WebM or MOV only' using errcode = '22023';
  end if;
  if p_max_mb is null or p_max_mb not between 1 and 50 then
    raise exception 'give the largest file as a whole number from 1 to 50 MB' using errcode = '22023';
  end if;
  if p_max_seconds is null or p_max_seconds not between 1 and 90 then
    raise exception 'give the longest pitch as a whole number from 1 to 90 seconds' using errcode = '22023';
  end if;
  select * into before_row from public.platform_settings for update;
  update public.platform_settings
     set pitch_types = types, pitch_max_mb = p_max_mb, pitch_max_seconds = p_max_seconds,
         updated_at = now(), updated_by = auth.uid();
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'settings.pitch', 'platform_settings', null,
          jsonb_build_object('pitch_types', before_row.pitch_types, 'pitch_max_mb', before_row.pitch_max_mb,
                             'pitch_max_seconds', before_row.pitch_max_seconds),
          jsonb_build_object('pitch_types', types, 'pitch_max_mb', p_max_mb, 'pitch_max_seconds', p_max_seconds));
end;
$$;

-- With introductions switched off, the daily limit is kept as it was when no
-- limit is given.
create or replace function public.admin_set_introduction_rules(p_on boolean, p_per_day integer) returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.platform_settings;
  per_day integer;
begin
  if not public.is_admin() then
    raise exception 'only admins can change the settings' using errcode = '42501';
  end if;
  if p_on is null then
    raise exception 'say whether introductions are on' using errcode = '22023';
  end if;
  select * into before_row from public.platform_settings for update;
  per_day := coalesce(p_per_day, case when not p_on then before_row.introductions_per_day end);
  if per_day is null or per_day < 1 then
    raise exception 'give the daily limit as a whole number of 1 or more' using errcode = '22023';
  end if;
  update public.platform_settings
     set introductions_on = p_on, introductions_per_day = per_day, updated_at = now(), updated_by = auth.uid();
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'settings.introductions', 'platform_settings', null,
          jsonb_build_object('introductions_on', before_row.introductions_on,
                             'introductions_per_day', before_row.introductions_per_day),
          jsonb_build_object('introductions_on', p_on, 'introductions_per_day', per_day));
end;
$$;

create or replace function public.admin_set_platform_mode(p_mode public.platform_mode, p_message text) returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.platform_settings;
  message text := btrim(coalesce(p_message, ''));
begin
  if not public.is_admin() then
    raise exception 'only admins can change the settings' using errcode = '42501';
  end if;
  if p_mode is null then
    raise exception 'choose live or maintenance' using errcode = '22023';
  end if;
  select * into before_row from public.platform_settings for update;
  if message = '' then
    if p_mode = 'maintenance' then
      raise exception 'write the message people will see' using errcode = '22023';
    end if;
    message := before_row.maintenance_message;
  end if;
  if char_length(message) > 280 then
    raise exception 'keep the message to 280 characters' using errcode = '22023';
  end if;
  update public.platform_settings
     set mode = p_mode, maintenance_message = message, updated_at = now(), updated_by = auth.uid();
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'settings.mode', 'platform_settings', null,
          jsonb_build_object('mode', before_row.mode, 'maintenance_message', before_row.maintenance_message),
          jsonb_build_object('mode', p_mode, 'maintenance_message', message));
end;
$$;

-- ---------------------------------------------------------------- 13. staff
-- Every active reviewer and admin. "Since" is the last time their role was
-- changed to a staff role, or when the account was made when it never was.
create or replace function public.admin_staff()
returns table (user_id uuid, full_name text, email text, role public.user_role, since timestamptz)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the staff list' using errcode = '42501';
  end if;
  return query
  select p.user_id, p.full_name, u.email::text, p.role,
    coalesce((select max(a.created_at) from public.audit_log a
              where a.action = 'account.role' and a.entity = 'profiles' and a.entity_id = p.user_id::text
                and a.after ->> 'role' in ('reviewer', 'admin')), p.created_at)
  from public.profiles p
  join auth.users u on u.id = p.user_id
  where p.role in ('reviewer', 'admin') and p.status = 'active'
  order by case p.role when 'admin' then 0 else 1 end, lower(p.full_name), p.user_id;
end;
$$;

-- Makes the account that uses an email address a reviewer or an admin, through
-- admin_set_role, which hides a founder's profile and writes the audit log.
create or replace function public.admin_staff_add(p_email text, p_role public.user_role) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  person public.profiles;
begin
  if not public.is_admin() then
    raise exception 'only admins can add staff' using errcode = '42501';
  end if;
  if p_role is null or p_role not in ('reviewer', 'admin') then
    raise exception 'choose reviewer or admin' using errcode = '22023';
  end if;
  select p.* into person
  from public.profiles p join auth.users u on u.id = p.user_id
  where lower(u.email::text) = lower(btrim(coalesce(p_email, '')));
  if person.user_id is null then
    raise exception 'no account uses this email address' using errcode = 'P0002';
  end if;
  if person.status <> 'active' then
    raise exception 'this account is not active' using errcode = 'P0001';
  end if;
  if person.role in ('reviewer', 'admin') then
    raise exception 'this account is on the staff list already' using errcode = 'P0001';
  end if;
  perform public.admin_set_role(person.user_id, p_role, 'Added to staff');
  return person.user_id;
end;
$$;

-- Takes a person off the staff list. A person with a venture becomes a founder
-- again. Anyone else is suspended, because an investor's access needs an
-- approval this cannot give, and an admin can then change the account on
-- People and roles.
create or replace function public.admin_staff_remove(p_user uuid) returns text
language plpgsql security definer set search_path = public as $$
declare
  person public.profiles;
begin
  if not public.is_admin() then
    raise exception 'only admins can remove staff' using errcode = '42501';
  end if;
  if p_user = auth.uid() then
    raise exception 'nobody can take themselves off the staff list' using errcode = '42501';
  end if;
  select * into person from public.profiles where user_id = p_user;
  if not found or person.role not in ('reviewer', 'admin') or person.status <> 'active' then
    raise exception 'this person is not on the staff list' using errcode = 'P0002';
  end if;
  if exists (select 1 from public.ventures where founder_id = p_user) then
    perform public.admin_set_role(p_user, 'founder', 'Removed from staff');
    return 'founder';
  end if;
  perform public.admin_set_status(p_user, 'suspended', 'Removed from staff');
  return 'suspended';
end;
$$;

-- ---------------------------------------------------------------- 14. the dashboard, analytics and audit
-- The counts beside the sidebar's sections, and whether sample data is held,
-- read on every admin page.
create or replace function public.admin_shell()
returns jsonb
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can see the admin pages' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'founders', (select count(*) from public.founder_register where not sample),
    'investors', (select count(*) from public.investor_register),
    'introductions', (select count(*) from public.register_introductions),
    'waitlist', (select coalesce(sum(responses_received), 0) from public.register_imports),
    'sample', exists (select 1 from public.founder_register where sample)
              or exists (select 1 from public.register_introductions where sample)
  );
end;
$$;

-- The counts the dashboard shows, in one call. The months run from January of
-- this year to this month. The register counts leave out the sample data, and
-- the introduction and message counts include it, as the design shows them.
create or replace function public.admin_dashboard()
returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare
  -- Months are counted in UTC, as the pages show the times.
  this_month timestamp := date_trunc('month', now() at time zone 'UTC');
begin
  if not public.is_admin() then
    raise exception 'only admins can see the dashboard' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'waitlist', (select coalesce(sum(responses_received), 0) from public.register_imports),
    'removed_as_test', (select coalesce(sum(removed_as_test), 0) from public.register_imports),
    'founders', (select count(*) from public.founder_register where not sample),
    'founders_with_support', (select count(*) from public.founder_register where not sample and cardinality(support) > 0),
    'investors', (select count(*) from public.investor_register),
    'videos', (select count(*) from public.pitch_video_files),
    'videos_pending', (select count(*) from public.pitch_video_files where status = 'pending'),
    'intros', (select count(*) from public.register_introductions),
    'intros_register', (select count(*) from public.register_introductions where not sample),
    'intros_pending', (select count(*) from public.register_introductions where status = 'pending'),
    'intros_accepted', (select count(*) from public.register_introductions where status = 'accepted'),
    'messages', (select coalesce(sum(messages), 0) from public.register_introductions),
    'conversations', (select count(*) from public.register_introductions where messages > 0),
    'admins', (select count(*) from public.profiles where role = 'admin' and status = 'active'),
    'reviewers', (select count(*) from public.profiles where role = 'reviewer' and status = 'active'),
    'evidence_waiting', (select count(*) from public.evidence where status in ('submitted', 'checking', 'needs_review')),
    'reports_open', (select count(*) from public.reports where status = 'open'),
    'investors_awaiting', (select count(*) from public.profiles where role = 'investor' and status = 'pending'),
    'unfinished', (select count(*) from auth.users u where not exists (select 1 from public.profiles p where p.user_id = u.id)),
    'sample', exists (select 1 from public.founder_register where sample)
              or exists (select 1 from public.register_introductions where sample),
    'months', (select jsonb_agg(jsonb_build_object(
        'month', to_char(m, 'YYYY-MM'),
        'founders', (select count(*) from public.founder_register f
                     where not f.sample and date_trunc('month', f.joined_at at time zone 'UTC') = m),
        'investors', (select count(*) from public.investor_register r
                      where date_trunc('month', r.registered_on::timestamp) = m))
        order by m)
      from generate_series(date_trunc('year', this_month), this_month, interval '1 month') m),
    'countries', (select coalesce(jsonb_agg(jsonb_build_array(c.country_key, c.n) order by c.n desc, c.country_key), '[]')
      from (select country_key, count(*) as n from public.founder_register where not sample group by country_key) c),
    'support', (select coalesce(jsonb_agg(jsonb_build_array(s.kind, s.n) order by s.n desc, s.kind), '[]')
      from (select kind, count(*) as n from public.founder_register, unnest(support) as kind
            where not sample group by kind having count(*) > 1) s),
    'latest_founder', (select jsonb_build_object('record_id', f.record_id, 'full_name', f.full_name,
        'startup', f.startup, 'joined_at', f.joined_at)
      from public.founder_register f where not f.sample order by f.joined_at desc, f.record_id desc limit 1),
    'latest_investor', (select jsonb_build_object('register_no', r.register_no, 'full_name', r.full_name,
        'registered_on', r.registered_on)
      from public.investor_register r order by r.registered_on desc, char_length(r.register_no) desc, r.register_no desc limit 1)
  );
end;
$$;

-- What the analytics page counts, for every founder and investor on the
-- registers. The page groups it by period, so it holds no names.
create or replace function public.admin_analytics_source()
returns jsonb
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can see the analytics' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'founders', (select coalesce(jsonb_agg(jsonb_build_object('record_id', f.record_id, 'joined_at', f.joined_at,
        'country', f.country_key, 'university', f.university, 'support', f.support) order by f.joined_at, f.record_id), '[]')
      from public.founder_register f where not f.sample),
    'investors', (select coalesce(jsonb_agg(r.registered_on order by r.registered_on), '[]') from public.investor_register r),
    'introductions', (select coalesce(jsonb_agg(jsonb_build_object('record_id', i.record_id, 'made_on', i.made_on,
        'status', i.status) order by i.made_on, i.intro_id), '[]')
      from public.register_introductions i where not i.sample),
    'videos', (select coalesce(jsonb_agg(v.added_on order by v.added_on), '[]') from public.pitch_video_files v)
  );
end;
$$;

-- The register's own history for the audit log page: each response to the
-- form, with what it said and the founder it belongs to, and each investor
-- added to the register, newest first. p_limit keeps the newest of each, for
-- the dashboard. Staff actions come from audit_log, which admins read directly.
create or replace function public.admin_register_history(p_limit integer default null)
returns jsonb
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the audit log' using errcode = '42501';
  end if;
  return jsonb_build_object(
    'responses', (select coalesce(jsonb_agg(x.entry order by x.responded_at desc, x.response_id desc), '[]')
      from (
        select w.responded_at, w.response_id, jsonb_build_object(
          'response_id', w.response_id, 'responded_at', w.responded_at, 'startup', w.startup, 'sector', w.sector,
          'first', not exists (
            select 1 from public.founder_register_responses e
            where e.record_id = w.record_id and (e.responded_at, e.response_id) < (w.responded_at, w.response_id)),
          'record_id', f.record_id, 'full_name', w.full_name, 'email', w.email, 'phone', w.phone,
          'country', w.country, 'university', w.university,
          'response_count', (select count(*) from public.founder_register_responses c where c.record_id = f.record_id)) as entry
        from public.founder_register_responses w join public.founder_register f on f.record_id = w.record_id
        where not f.sample
        order by w.responded_at desc, w.response_id desc
        limit p_limit
      ) x),
    'investors', (select coalesce(jsonb_agg(x.entry order by x.registered_on desc, char_length(x.register_no) desc, x.register_no desc), '[]')
      from (
        select r.registered_on, r.register_no,
          jsonb_build_object('register_no', r.register_no, 'full_name', r.full_name, 'registered_on', r.registered_on) as entry
        from public.investor_register r
        order by r.registered_on desc, char_length(r.register_no) desc, r.register_no desc
        limit p_limit
      ) x)
  );
end;
$$;

-- ---------------------------------------------------------------- 15. the database page
-- Each table in public with its exact row count and whether row level security
-- is on, each column, the stored files by bucket, and the migrations Supabase
-- recorded with the name of the latest.
-- Message text and other values are never read here, only counted.
create or replace function public.admin_database()
returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare
  t record;
  n bigint;
  tables jsonb := '[]';
  migrations jsonb := null;
begin
  if not public.is_admin() then
    raise exception 'only admins can see the database page' using errcode = '42501';
  end if;
  for t in
    select c.relname, c.relrowsecurity
    from pg_class c join pg_namespace s on s.oid = c.relnamespace
    where s.nspname = 'public' and c.relkind = 'r'
    order by c.relname
  loop
    execute format('select count(*) from public.%I', t.relname) into n;
    tables := tables || jsonb_build_object(
      'name', t.relname, 'rows', n, 'rls', t.relrowsecurity,
      'columns', (select jsonb_agg(a.attname::text order by a.attnum) from pg_attribute a
                  where a.attrelid = ('public.' || quote_ident(t.relname))::regclass and a.attnum > 0 and not a.attisdropped));
  end loop;
  if to_regclass('supabase_migrations.schema_migrations') is not null then
    execute 'select jsonb_build_object(''count'', count(*), ''latest'', max(version),
               ''name'', (array_agg(name order by version desc))[1]) from supabase_migrations.schema_migrations'
      into migrations;
  end if;
  return jsonb_build_object(
    'version', current_setting('server_version'),
    'tables', tables,
    'buckets', (select coalesce(jsonb_agg(jsonb_build_object('id', b.id,
        'files', (select count(*) from storage.objects o where o.bucket_id = b.id)) order by b.id), '[]')
      from storage.buckets b),
    'migrations', migrations
  );
end;
$$;

-- ---------------------------------------------------------------- rights
revoke execute on function public.guard_register_introduction() from public, anon, authenticated;
revoke execute on function public.guard_pitch_rules() from public, anon, authenticated;
revoke execute on function public.prepare_introduction() from public, anon, authenticated;
revoke execute on function public.platform_status() from public;
grant execute on function public.platform_status() to anon, authenticated;
revoke execute on function public.report_conversation(uuid, text) from public, anon;
grant execute on function public.report_conversation(uuid, text) to authenticated;

do $$
declare
  f text;
begin
  foreach f in array array[
    'public.admin_founder_records(boolean)', 'public.admin_founder_record(text)',
    'public.admin_founder_record_delete(text)', 'public.admin_unfinished_signups()', 'public.admin_remove_signup(uuid)',
    'public.admin_register(text, date, integer, integer, text)', 'public.admin_register_link(text, text)',
    'public.admin_register_unlink(text)', 'public.admin_register_introductions(text)',
    'public.admin_register_introduction_status(text, public.register_intro_status)', 'public.admin_pitch_videos()',
    'public.admin_pitch_video_decide(text, public.video_review_status, jsonb, text)', 'public.admin_pitch_video_reopen(text)',
    'public.admin_reports(boolean)', 'public.admin_report_resolve(uuid, text)', 'public.admin_settings()',
    'public.admin_set_pitch_rules(text[], integer, integer)', 'public.admin_set_introduction_rules(boolean, integer)',
    'public.admin_set_platform_mode(public.platform_mode, text)', 'public.admin_staff()',
    'public.admin_staff_add(text, public.user_role)', 'public.admin_staff_remove(uuid)', 'public.admin_shell()',
    'public.admin_dashboard()',
    'public.admin_analytics_source()', 'public.admin_register_history(integer)', 'public.admin_database()'
  ] loop
    execute format('revoke execute on function %s from public, anon', f);
    execute format('grant execute on function %s to authenticated', f);
  end loop;
end $$;

-- Every new table is closed to anon and authenticated, and every function
-- that writes checks the caller first. This fails the migration if either is
-- not so.
do $$
declare
  bad text;
begin
  select string_agg(c.relname, ', ') into bad
  from pg_class c join pg_namespace s on s.oid = c.relnamespace
  where s.nspname = 'public' and c.relkind = 'r'
    and c.relname in ('founder_register', 'founder_register_responses', 'register_imports', 'register_introductions',
                      'pitch_video_files', 'reports', 'platform_settings')
    and (not c.relrowsecurity
         or has_table_privilege('anon', c.oid, 'select') or has_table_privilege('authenticated', c.oid, 'select')
         or has_table_privilege('anon', c.oid, 'insert') or has_table_privilege('authenticated', c.oid, 'insert'));
  if bad is not null then
    raise exception 'these tables are open to anon or authenticated: %', bad;
  end if;
end $$;
