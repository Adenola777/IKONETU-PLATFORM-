-- IkonetU core schema, release 1 and 2 (TRD Data model).
-- Every table holding user data has row-level security (SRD SEC-I3).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Types
-- ---------------------------------------------------------------------------
create type public.user_role as enum ('founder', 'investor', 'mentor', 'reviewer', 'admin');
create type public.account_status as enum ('active', 'pending', 'suspended');
create type public.country_code as enum ('NG', 'GH', 'KE');
create type public.product_stage as enum ('idea', 'mvp', 'revenue', 'scaling');
create type public.evidence_status as enum ('submitted', 'checking', 'needs_review', 'needs_more', 'approved', 'rejected', 'expired');
create type public.evidence_lane as enum ('government', 'source', 'ai', 'human', 'human_confirmed', 'self');
create type public.league as enum ('EARLY', 'RISING', 'INVESTABLE', 'ELITE');
create type public.waitlist_role as enum ('founder', 'investor', 'mentor');

-- ---------------------------------------------------------------------------
-- Shared helpers
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Waitlist (PRD L-1). Written only by the API with the service role key.
-- ---------------------------------------------------------------------------
create table public.waitlist (
  id uuid primary key default gen_random_uuid(),
  full_name text not null check (char_length(full_name) between 2 and 120),
  contact text not null check (char_length(contact) between 5 and 160),
  contact_type text not null check (contact_type in ('phone', 'email')),
  country public.country_code not null,
  role public.waitlist_role not null,
  confirmed_adult boolean not null check (confirmed_adult),
  privacy_version text not null,
  source text,
  created_at timestamptz not null default now(),
  unique (contact)
);
alter table public.waitlist enable row level security;
-- No policies: anon and authenticated users cannot read or write the waitlist.

-- ---------------------------------------------------------------------------
-- Profiles (one per Supabase Auth user)
-- ---------------------------------------------------------------------------
create table public.profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  role public.user_role not null default 'founder',
  status public.account_status not null default 'active',
  full_name text not null check (char_length(full_name) between 2 and 120),
  country public.country_code,
  city text,
  institution text,
  graduate_status text,
  bio text check (char_length(bio) <= 600),
  avatar_path text,
  confirmed_adult boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger profiles_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();
alter table public.profiles enable row level security;

create or replace function public.app_role() returns public.user_role
language sql stable security definer set search_path = public as $$
  select role from public.profiles where user_id = auth.uid() and status = 'active';
$$;

create or replace function public.is_staff() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(public.app_role() in ('reviewer', 'admin'), false);
$$;

create policy "profiles: read own or staff" on public.profiles
  for select using (user_id = auth.uid() or public.is_staff());
create policy "profiles: create own as founder" on public.profiles
  for insert with check (user_id = auth.uid() and role = 'founder' and status = 'active');
create policy "profiles: update own" on public.profiles
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Users may not change their own role or status. Only the service role or admins can.
create or replace function public.guard_profile_privileges() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (new.role is distinct from old.role or new.status is distinct from old.status)
     and coalesce(auth.role(), '') <> 'service_role'
     and coalesce(public.app_role() = 'admin', false) = false then
    raise exception 'role and status can only be changed by an admin';
  end if;
  return new;
end;
$$;
create trigger profiles_guard_privileges before update on public.profiles
  for each row execute function public.guard_profile_privileges();

-- Public, non-sensitive founder card (PRD P-4). Exposes no contact details.
create view public.public_profiles with (security_invoker = false) as
  select p.user_id, p.full_name, p.country, p.city, p.institution, p.bio, p.avatar_path
  from public.profiles p
  where p.status = 'active' and p.role = 'founder';
grant select on public.public_profiles to authenticated;

-- ---------------------------------------------------------------------------
-- Consents (SRD SEC-D4, SEC-D5)
-- ---------------------------------------------------------------------------
create table public.consents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  consent_type text not null check (consent_type in ('profile', 'evidence_processing', 'registry_check', 'bank_check', 'notifications', 'marketing')),
  granted boolean not null,
  policy_version text not null,
  granted_at timestamptz not null default now(),
  withdrawn_at timestamptz
);
create index consents_user_idx on public.consents (user_id, consent_type);
alter table public.consents enable row level security;
create policy "consents: read own" on public.consents for select using (user_id = auth.uid());
create policy "consents: record own" on public.consents for insert with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Ventures
-- ---------------------------------------------------------------------------
create table public.ventures (
  id uuid primary key default gen_random_uuid(),
  founder_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  sector text not null,
  stage public.product_stage not null default 'idea',
  country public.country_code not null,
  registration_number text,
  website text,
  social_links jsonb not null default '{}'::jsonb,
  description text check (char_length(description) <= 280),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ventures_founder_idx on public.ventures (founder_id);
create trigger ventures_updated_at before update on public.ventures
  for each row execute function public.set_updated_at();
alter table public.ventures enable row level security;
create policy "ventures: read by signed-in users" on public.ventures
  for select to authenticated using (true);
create policy "ventures: create own" on public.ventures
  for insert with check (founder_id = auth.uid());
create policy "ventures: update own" on public.ventures
  for update using (founder_id = auth.uid()) with check (founder_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Rubric (values mirror packages/score-engine/src/rubric.ts)
-- ---------------------------------------------------------------------------
create table public.rubric_versions (
  version text primary key,
  is_active boolean not null default false,
  published_at timestamptz not null default now()
);
create unique index rubric_one_active on public.rubric_versions (is_active) where is_active;

create table public.rubric_signals (
  rubric_version text not null references public.rubric_versions (version),
  code text not null,
  category text not null,
  label text not null,
  mode text not null check (mode in ('fixed', 'per_item', 'months', 'revenue', 'stage')),
  points numeric not null,
  max_points numeric not null,
  usd_per_point numeric,
  stage_points jsonb,
  expiry_days integer,
  primary key (rubric_version, code)
);
alter table public.rubric_versions enable row level security;
alter table public.rubric_signals enable row level security;
create policy "rubric versions: readable" on public.rubric_versions for select using (true);
create policy "rubric signals: readable" on public.rubric_signals for select using (true);

-- ---------------------------------------------------------------------------
-- Evidence (PRD E-1 to E-9). Founders submit; only the server decides.
-- ---------------------------------------------------------------------------
create table public.evidence (
  id uuid primary key default gen_random_uuid(),
  venture_id uuid not null references public.ventures (id) on delete cascade,
  signal_code text not null,
  status public.evidence_status not null default 'submitted',
  lane public.evidence_lane,
  item_count integer check (item_count is null or item_count >= 0),
  months integer check (months is null or months >= 0),
  revenue_usd numeric check (revenue_usd is null or revenue_usd >= 0),
  fx_rate_usd numeric,
  stage public.product_stage,
  source_ref text,
  ai_result jsonb,
  ai_confidence text check (ai_confidence in ('high', 'medium', 'low')),
  decided_by uuid references auth.users (id),
  decided_at timestamptz,
  reason text,
  expires_at timestamptz,
  appeal_of uuid references public.evidence (id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index evidence_venture_idx on public.evidence (venture_id, status);
create index evidence_queue_idx on public.evidence (status, created_at) where status = 'needs_review';
create trigger evidence_updated_at before update on public.evidence
  for each row execute function public.set_updated_at();
alter table public.evidence enable row level security;

create or replace function public.owns_venture(v uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.ventures where id = v and founder_id = auth.uid());
$$;

create policy "evidence: founder reads own, staff read all" on public.evidence
  for select using (public.owns_venture(venture_id) or public.is_staff());
create policy "evidence: founder submits own" on public.evidence
  for insert with check (
    public.owns_venture(venture_id)
    and status = 'submitted'
    and lane is null
    and decided_by is null
    and ai_result is null
  );
-- No update or delete policies for founders. Decisions are written by the API (service role).

create table public.evidence_files (
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references public.evidence (id) on delete cascade,
  storage_path text not null unique,
  sha256 text not null,
  mime_type text not null check (mime_type in ('application/pdf', 'image/jpeg', 'image/png')),
  size_bytes integer not null check (size_bytes > 0 and size_bytes <= 10485760),
  created_at timestamptz not null default now()
);
create index evidence_files_sha_idx on public.evidence_files (sha256);
alter table public.evidence_files enable row level security;
create policy "evidence files: founder reads own, staff read all" on public.evidence_files
  for select using (
    public.is_staff()
    or exists (select 1 from public.evidence e where e.id = evidence_id and public.owns_venture(e.venture_id))
  );

create table public.verification_checks (
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references public.evidence (id) on delete cascade,
  provider text not null,
  request_ref text,
  matched boolean,
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
alter table public.verification_checks enable row level security;
create policy "verification checks: staff only" on public.verification_checks
  for select using (public.is_staff());

create table public.reviews (
  id uuid primary key default gen_random_uuid(),
  evidence_id uuid not null references public.evidence (id) on delete cascade,
  reviewer_id uuid not null references auth.users (id),
  decision text not null check (decision in ('approve', 'reject', 'needs_more')),
  reason text,
  is_sample_audit boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.reviews enable row level security;
create policy "reviews: staff only" on public.reviews for select using (public.is_staff());

-- ---------------------------------------------------------------------------
-- Scores. One current row per venture plus an append-only history.
-- ---------------------------------------------------------------------------
create table public.scores (
  venture_id uuid primary key references public.ventures (id) on delete cascade,
  total integer not null check (total between 0 and 1000),
  league public.league not null,
  categories jsonb not null,
  rubric_version text not null,
  computed_at timestamptz not null default now()
);
alter table public.scores enable row level security;
create policy "scores: readable by signed-in users" on public.scores
  for select to authenticated using (true);

create table public.score_events (
  id bigint generated always as identity primary key,
  venture_id uuid not null references public.ventures (id) on delete cascade,
  total integer not null,
  league public.league not null,
  delta integer not null,
  cause_evidence_id uuid references public.evidence (id),
  created_at timestamptz not null default now()
);
create index score_events_venture_idx on public.score_events (venture_id, created_at);
alter table public.score_events enable row level security;
create policy "score events: founder reads own, staff read all" on public.score_events
  for select using (public.owns_venture(venture_id) or public.is_staff());

create or replace function public.forbid_change() returns trigger
language plpgsql as $$
begin
  raise exception '% is append-only', tg_table_name;
end;
$$;
create trigger score_events_append_only before update or delete on public.score_events
  for each row execute function public.forbid_change();

-- ---------------------------------------------------------------------------
-- Audit log (SRD SEC-I5). Append-only, admins read.
-- ---------------------------------------------------------------------------
create table public.audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid references auth.users (id),
  action text not null,
  entity text not null,
  entity_id text,
  before jsonb,
  after jsonb,
  created_at timestamptz not null default now()
);
alter table public.audit_log enable row level security;
create policy "audit log: admins read" on public.audit_log
  for select using (public.app_role() = 'admin');
create trigger audit_log_append_only before update or delete on public.audit_log
  for each row execute function public.forbid_change();

-- ---------------------------------------------------------------------------
-- Evidence storage (SRD SEC-E1, SEC-E2, SEC-E5). Private bucket; files sit
-- under evidence/<user id>/<random id>, so a path never carries a name.
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('evidence', 'evidence', false, 10485760, array['application/pdf', 'image/jpeg', 'image/png'])
on conflict (id) do nothing;

create policy "evidence bucket: founder uploads to own folder" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'evidence' and (storage.foldername(name))[1] = auth.uid()::text);
-- Reads go through 5-minute signed links issued by the API, so no select policy is granted.
