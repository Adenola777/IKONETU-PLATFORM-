-- ---------------------------------------------------------------------------
-- The investor side, and the founder pieces it reads. Written 15 October 2026.
--
-- The owner chose on 15 October 2026 that investors sign up and wait for an
-- admin's approval (PRD A-3), that pitches live in a private Supabase Storage
-- bucket, and that investors see evidence by area with no score, league or
-- ranking. docs/DECISIONS.md records each choice.
--
-- What an approved investor can read: ventures the founder has published, the
-- founder card, the pitch, progress updates, and the evidence through
-- venture_evidence(), which shows one of three statuses and never the files,
-- the reviewer or the founder-facing reason. Rejected, expired and "needs
-- more" evidence is never shown to investors.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- New columns first, because the helpers below read them.
-- ---------------------------------------------------------------------------
-- A venture is visible to approved investors only while published_at is set.
alter table public.ventures add column published_at timestamptz;

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------
create or replace function public.is_approved_investor() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(public.app_role() = 'investor', false);
$$;

-- True when the venture is published and the person asking is an approved investor.
create or replace function public.venture_visible_to_investor(v uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select public.is_approved_investor()
     and exists (select 1 from public.ventures where id = v and published_at is not null);
$$;

-- The same test by founder, for storage paths that start with the founder's id.
-- It takes text, so a folder name that is not an id can never raise an error.
create or replace function public.founder_visible_to_investor(founder text) returns boolean
language sql stable security definer set search_path = public as $$
  select public.is_approved_investor()
     and exists (select 1 from public.ventures where founder_id::text = founder and published_at is not null);
$$;

-- ---------------------------------------------------------------------------
-- Sign-up. A person creates their own profile as a founder, who is active at
-- once, or as an investor, who stays pending until an admin approves them.
-- app_role() only returns the role of an active profile, so a pending
-- investor can read nothing an investor can.
-- ---------------------------------------------------------------------------
drop policy "profiles: create own as founder" on public.profiles;
create policy "profiles: create own as founder or pending investor" on public.profiles
  for insert with check (
    user_id = auth.uid()
    and ((role = 'founder' and status = 'active') or (role = 'investor' and status = 'pending'))
  );

-- ---------------------------------------------------------------------------
-- Investor profiles
-- ---------------------------------------------------------------------------
create table public.investor_profiles (
  user_id uuid primary key references public.profiles (user_id) on delete cascade,
  investor_type text not null check (investor_type in ('individual', 'angel', 'fund')),
  firm text check (firm is null or char_length(firm) between 1 and 120),
  website text check (website is null or char_length(website) <= 200),
  based_in text not null check (based_in in ('NG', 'GH', 'KE', 'other')),
  sectors text[] not null check (
    cardinality(sectors) between 1 and 5
    and sectors <@ array['Fintech', 'Agritech', 'Edtech', 'Health', 'Other']::text[]
  ),
  stages public.product_stage[] not null default '{}' check (cardinality(stages) <= 4),
  countries public.country_code[] not null default '{}' check (cardinality(countries) <= 3),
  cheque_size text not null check (
    cheque_size in ('Under $25,000', '$25,000 to $100,000', '$100,000 to $500,000', 'Over $500,000', 'Prefer not to say')
  ),
  thesis text check (thesis is null or char_length(thesis) <= 600),
  confirmed_statement boolean not null check (confirmed_statement),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger investor_profiles_updated_at before update on public.investor_profiles
  for each row execute function public.set_updated_at();
alter table public.investor_profiles enable row level security;
create policy "investor profiles: read own or staff" on public.investor_profiles
  for select using (user_id = auth.uid() or public.is_staff());
create policy "investor profiles: create own" on public.investor_profiles
  for insert with check (
    user_id = auth.uid()
    and exists (select 1 from public.profiles p where p.user_id = auth.uid() and p.role = 'investor')
  );
create policy "investor profiles: update own" on public.investor_profiles
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

-- An admin approves or declines a pending investor. A declined investor is
-- suspended, and can be approved later. Each decision goes to the audit log.
create or replace function public.decide_investor(p_user uuid, p_approve boolean) returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.profiles;
  after_row public.profiles;
begin
  if coalesce(public.app_role() = 'admin', false) = false then
    raise exception 'only admins can approve investors' using errcode = '42501';
  end if;
  select * into before_row from public.profiles where user_id = p_user and role = 'investor' for update;
  if not found then
    raise exception 'investor not found' using errcode = 'P0002';
  end if;
  update public.profiles
     set status = case when p_approve then 'active'::public.account_status else 'suspended'::public.account_status end
   where user_id = p_user
  returning * into after_row;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), case when p_approve then 'investor.approve' else 'investor.decline' end, 'profiles',
          p_user::text, jsonb_build_object('status', before_row.status), jsonb_build_object('status', after_row.status));
end;
$$;

-- ---------------------------------------------------------------------------
-- Ventures: the founder publishes or hides their profile. Only published
-- ventures are visible to approved investors. Other founders no longer see
-- each other's ventures.
-- ---------------------------------------------------------------------------
-- Discovery filters by sector, so new and changed ventures take one of the
-- sectors the investor interest form uses. Existing rows are not checked.
alter table public.ventures add constraint ventures_sector_known
  check (sector in ('Fintech', 'Agritech', 'Edtech', 'Health', 'Other')) not valid;

drop policy "ventures: read by signed-in users" on public.ventures;
create policy "ventures: read own, staff, or published to approved investors" on public.ventures
  for select to authenticated using (
    founder_id = auth.uid() or public.is_staff() or (published_at is not null and public.is_approved_investor())
  );

-- Scores are for the founder and staff. Investors see evidence by area instead.
drop policy "scores: readable by signed-in users" on public.scores;
create policy "scores: founder reads own, staff read all" on public.scores
  for select using (public.owns_venture(venture_id) or public.is_staff());

-- The founder card. It now shows only to the founder, staff and approved
-- investors, and only for a founder who has published a venture.
create or replace view public.public_profiles with (security_invoker = false) as
  select p.user_id, p.full_name, p.country, p.city, p.institution, p.bio, p.avatar_path
  from public.profiles p
  where p.status = 'active' and p.role = 'founder'
    and (
      p.user_id = auth.uid()
      or public.is_staff()
      or (public.is_approved_investor()
          and exists (select 1 from public.ventures v where v.founder_id = p.user_id and v.published_at is not null))
    );

-- ---------------------------------------------------------------------------
-- Pitches. One current pitch per venture, in a private bucket. Files sit
-- under pitches/<founder id>/<random id>. The founder types the transcript,
-- and the captions are made from it.
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('pitches', 'pitches', false, 52428800, array['video/mp4', 'video/webm', 'video/quicktime'])
on conflict (id) do nothing;

create table public.pitches (
  venture_id uuid primary key references public.ventures (id) on delete cascade,
  storage_path text not null unique,
  mime_type text not null check (mime_type in ('video/mp4', 'video/webm', 'video/quicktime')),
  size_bytes integer not null check (size_bytes > 0 and size_bytes <= 52428800),
  duration_seconds numeric not null check (duration_seconds > 0 and duration_seconds <= 90),
  transcript text not null check (char_length(transcript) between 20 and 2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger pitches_updated_at before update on public.pitches
  for each row execute function public.set_updated_at();
alter table public.pitches enable row level security;
create policy "pitches: read own, staff, or published to approved investors" on public.pitches
  for select using (public.owns_venture(venture_id) or public.is_staff() or public.venture_visible_to_investor(venture_id));
create policy "pitches: founder adds own" on public.pitches
  for insert with check (public.owns_venture(venture_id) and split_part(storage_path, '/', 1) = auth.uid()::text);
create policy "pitches: founder replaces own" on public.pitches
  for update using (public.owns_venture(venture_id))
  with check (public.owns_venture(venture_id) and split_part(storage_path, '/', 1) = auth.uid()::text);
create policy "pitches: founder removes own" on public.pitches
  for delete using (public.owns_venture(venture_id));

create policy "pitches bucket: founder uploads to own folder" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'pitches' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "pitches bucket: read own, staff, or approved investors" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'pitches'
    and ((storage.foldername(name))[1] = auth.uid()::text
         or public.is_staff()
         or public.founder_visible_to_investor((storage.foldername(name))[1]))
  );
create policy "pitches bucket: founder removes own" on storage.objects
  for delete to authenticated
  using (bucket_id = 'pitches' and (storage.foldername(name))[1] = auth.uid()::text);

-- A venture can only be published once it has a pitch.
create or replace function public.guard_publish() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.published_at is not null and old.published_at is null
     and not exists (select 1 from public.pitches where venture_id = new.id) then
    raise exception 'add a pitch before publishing' using errcode = 'P0001';
  end if;
  return new;
end;
$$;
create trigger ventures_guard_publish before update on public.ventures
  for each row execute function public.guard_publish();

-- ---------------------------------------------------------------------------
-- Progress updates. They show investors who is still building.
-- ---------------------------------------------------------------------------
create table public.venture_updates (
  id uuid primary key default gen_random_uuid(),
  venture_id uuid not null references public.ventures (id) on delete cascade,
  body text not null check (char_length(body) between 10 and 600),
  created_at timestamptz not null default now()
);
create index venture_updates_venture_idx on public.venture_updates (venture_id, created_at desc);
alter table public.venture_updates enable row level security;
create policy "updates: read own, staff, or published to approved investors" on public.venture_updates
  for select using (public.owns_venture(venture_id) or public.is_staff() or public.venture_visible_to_investor(venture_id));
create policy "updates: founder posts own" on public.venture_updates
  for insert with check (public.owns_venture(venture_id));
create policy "updates: founder removes own" on public.venture_updates
  for delete using (public.owns_venture(venture_id));

-- ---------------------------------------------------------------------------
-- Evidence. The founder adds a short summary. The reviewer adds a public note
-- saying what was compared, which investors see. A founder can now record the
-- files of their own evidence, and staff can open evidence files.
-- ---------------------------------------------------------------------------
alter table public.evidence add column summary text check (summary is null or char_length(summary) <= 280);
alter table public.evidence add column public_note text check (public_note is null or char_length(public_note) <= 280);

drop policy "evidence: founder submits own" on public.evidence;
create policy "evidence: founder submits own" on public.evidence
  for insert with check (
    public.owns_venture(venture_id)
    and status = 'submitted'
    and lane is null
    and decided_by is null
    and decided_at is null
    and ai_result is null
    and ai_confidence is null
    and public_note is null
    and reason is null
    and expires_at is null
  );

create policy "evidence files: founder records own" on public.evidence_files
  for insert with check (
    split_part(storage_path, '/', 1) = auth.uid()::text
    and exists (
      select 1 from public.evidence e
      where e.id = evidence_id and e.status = 'submitted' and public.owns_venture(e.venture_id)
    )
  );

create policy "evidence bucket: staff read" on storage.objects
  for select to authenticated
  using (bucket_id = 'evidence' and public.is_staff());

-- The evidence an investor may see, for one venture. Each item shows one of
-- three statuses: third_party (approved from a registry or other outside
-- source), reviewed (approved by an IkonetU reviewer) or submitted (not yet
-- decided). Files, reviewer, reason and AI results are never returned.
create or replace function public.venture_evidence(p_venture uuid)
returns table (
  id uuid, signal_code text, category text, label text, summary text,
  shown_status text, public_note text, reviewed_at timestamptz, created_at timestamptz
)
language sql stable security definer set search_path = public as $$
  select e.id, e.signal_code, s.category, s.label, e.summary,
    case
      when e.status = 'approved' and e.lane in ('government', 'source') then 'third_party'
      when e.status = 'approved' then 'reviewed'
      else 'submitted'
    end,
    case when e.status = 'approved' then e.public_note end,
    case when e.status = 'approved' then e.decided_at end,
    e.created_at
  from public.evidence e
  join public.ventures v on v.id = e.venture_id
  join public.rubric_versions rv on rv.is_active
  join public.rubric_signals s on s.rubric_version = rv.version and s.code = e.signal_code
  where e.venture_id = p_venture
    and (
      e.status in ('submitted', 'checking', 'needs_review')
      or (e.status = 'approved'
          and e.lane in ('government', 'source', 'human', 'human_confirmed')
          and (e.expires_at is null or e.expires_at > now()))
    )
    and (v.founder_id = auth.uid() or public.is_staff() or (v.published_at is not null and public.is_approved_investor()))
  order by s.category, e.created_at;
$$;

-- A staff decision on one piece of evidence. Approval needs a lane and a note
-- of what was compared. A rejection or a request for more needs a reason for
-- the founder. Nobody decides their own evidence. Each decision is written
-- to reviews and to the audit log.
create or replace function public.decide_evidence(
  p_evidence uuid,
  p_decision text,
  p_lane public.evidence_lane default null,
  p_public_note text default null,
  p_reason text default null,
  p_item_count integer default null,
  p_months integer default null,
  p_revenue_usd numeric default null,
  p_stage public.product_stage default null
) returns void
language plpgsql security definer set search_path = public as $$
declare
  e public.evidence;
  after_row public.evidence;
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can decide evidence' using errcode = '42501';
  end if;
  select * into e from public.evidence where id = p_evidence for update;
  if not found then
    raise exception 'evidence not found' using errcode = 'P0002';
  end if;
  if exists (select 1 from public.ventures where id = e.venture_id and founder_id = auth.uid()) then
    raise exception 'nobody can decide their own evidence' using errcode = '42501';
  end if;
  if e.status not in ('submitted', 'checking', 'needs_review') then
    raise exception 'this evidence has already been decided' using errcode = 'P0001';
  end if;

  if p_decision = 'approve' then
    if p_lane is null or p_lane not in ('government', 'source', 'human') then
      raise exception 'choose how the evidence was checked' using errcode = '22023';
    end if;
    if char_length(trim(coalesce(p_public_note, ''))) < 5 then
      raise exception 'say what was compared' using errcode = '22023';
    end if;
    update public.evidence set
      status = 'approved', lane = p_lane, public_note = left(trim(p_public_note), 280), reason = null,
      decided_by = auth.uid(), decided_at = now(),
      item_count = coalesce(p_item_count, item_count), months = coalesce(p_months, months),
      revenue_usd = coalesce(p_revenue_usd, revenue_usd), stage = coalesce(p_stage, stage)
    where id = p_evidence
    returning * into after_row;
  elsif p_decision in ('reject', 'needs_more') then
    if char_length(trim(coalesce(p_reason, ''))) < 5 then
      raise exception 'give the founder a reason' using errcode = '22023';
    end if;
    update public.evidence set
      status = case when p_decision = 'reject' then 'rejected'::public.evidence_status else 'needs_more'::public.evidence_status end,
      reason = trim(p_reason), decided_by = auth.uid(), decided_at = now()
    where id = p_evidence
    returning * into after_row;
  else
    raise exception 'unknown decision' using errcode = '22023';
  end if;

  insert into public.reviews (evidence_id, reviewer_id, decision, reason)
  values (p_evidence, auth.uid(), p_decision, coalesce(nullif(trim(p_reason), ''), trim(p_public_note)));
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'evidence.' || p_decision, 'evidence', p_evidence::text,
          jsonb_build_object('status', e.status, 'lane', e.lane),
          jsonb_build_object('status', after_row.status, 'lane', after_row.lane, 'public_note', after_row.public_note));
end;
$$;

-- Staff record the score the score engine computed after a decision. The
-- history row keeps the change, and the current row is replaced.
create or replace function public.record_score(
  p_venture uuid, p_total integer, p_league public.league, p_categories jsonb, p_rubric text, p_cause uuid default null
) returns void
language plpgsql security definer set search_path = public as $$
declare
  old_total integer;
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can record a score' using errcode = '42501';
  end if;
  select total into old_total from public.scores where venture_id = p_venture;
  if old_total is not distinct from p_total then
    update public.scores set league = p_league, categories = p_categories, rubric_version = p_rubric, computed_at = now()
     where venture_id = p_venture;
    return;
  end if;
  insert into public.scores (venture_id, total, league, categories, rubric_version, computed_at)
  values (p_venture, p_total, p_league, p_categories, p_rubric, now())
  on conflict (venture_id) do update set
    total = excluded.total, league = excluded.league, categories = excluded.categories,
    rubric_version = excluded.rubric_version, computed_at = excluded.computed_at;
  insert into public.score_events (venture_id, total, league, delta, cause_evidence_id)
  values (p_venture, p_total, p_league, p_total - coalesce(old_total, 0), p_cause);
end;
$$;

-- ---------------------------------------------------------------------------
-- Discovery. Published ventures for approved investors and staff, filtered
-- and sorted by company name, never by a score. Choices inside one filter
-- widen the list, and filters across groups narrow it.
-- p_evidence takes 'revenue_reviewed', 'registry_record' and 'any_reviewed'.
-- ---------------------------------------------------------------------------
create or replace function public.discover_ventures(
  p_sectors text[] default null,
  p_stages public.product_stage[] default null,
  p_countries public.country_code[] default null,
  p_evidence text[] default null,
  p_active_days integer default null,
  p_limit integer default 50,
  p_offset integer default 0
)
returns table (
  venture_id uuid, name text, sector text, stage public.product_stage, country public.country_code,
  description text, founder_name text, city text, pitch_seconds numeric, last_activity timestamptz,
  updates_90d integer, areas jsonb, total_count bigint
)
language sql stable security definer set search_path = public as $$
  with visible as (
    select v.*
    from public.ventures v
    join public.profiles p on p.user_id = v.founder_id and p.status = 'active' and p.role = 'founder'
    where v.published_at is not null
      and (public.is_approved_investor() or public.is_staff())
  ),
  ev as (
    select e.venture_id, s.category, e.signal_code, e.created_at,
      case
        when e.status = 'approved' and e.lane in ('government', 'source') then 3
        when e.status = 'approved' then 2
        else 1
      end as rank
    from public.evidence e
    join visible v on v.id = e.venture_id
    join public.rubric_versions rv on rv.is_active
    join public.rubric_signals s on s.rubric_version = rv.version and s.code = e.signal_code
    where e.status in ('submitted', 'checking', 'needs_review')
       or (e.status = 'approved'
           and e.lane in ('government', 'source', 'human', 'human_confirmed')
           and (e.expires_at is null or e.expires_at > now()))
  ),
  areas as (
    select venture_id,
      jsonb_agg(jsonb_build_object(
        'category', category,
        'status', case best when 3 then 'third_party' when 2 then 'reviewed' else 'submitted' end,
        'count', n) order by category) as areas
    from (select venture_id, category, max(rank) as best, count(*) as n from ev group by venture_id, category) a
    group by venture_id
  ),
  activity as (
    select v.id,
      greatest(
        v.published_at,
        (select max(u.created_at) from public.venture_updates u where u.venture_id = v.id),
        (select pi.updated_at from public.pitches pi where pi.venture_id = v.id),
        (select max(ev.created_at) from ev where ev.venture_id = v.id)
      ) as last_activity,
      (select count(*)::integer from public.venture_updates u where u.venture_id = v.id and u.created_at > now() - interval '90 days') as updates_90d
    from visible v
  ),
  matched as (
    select v.id, v.name, v.sector, v.stage, v.country, v.description, p.full_name, p.city,
      pi.duration_seconds, a.last_activity, a.updates_90d, coalesce(ar.areas, '[]'::jsonb) as areas
    from visible v
    join public.profiles p on p.user_id = v.founder_id
    join activity a on a.id = v.id
    left join public.pitches pi on pi.venture_id = v.id
    left join areas ar on ar.venture_id = v.id
    where (p_sectors is null or cardinality(p_sectors) = 0 or v.sector = any (p_sectors))
      and (p_stages is null or cardinality(p_stages) = 0 or v.stage = any (p_stages))
      and (p_countries is null or cardinality(p_countries) = 0 or v.country = any (p_countries))
      and (p_active_days is null or a.last_activity > now() - make_interval(days => p_active_days))
      and (p_evidence is null or cardinality(p_evidence) = 0 or (
        ('revenue_reviewed' = any (p_evidence) and exists (
          select 1 from ev where ev.venture_id = v.id and ev.signal_code = 'revenue' and ev.rank >= 2))
        or ('registry_record' = any (p_evidence) and exists (
          select 1 from ev where ev.venture_id = v.id and ev.signal_code = 'company_registration' and ev.rank = 3))
        or ('any_reviewed' = any (p_evidence) and exists (
          select 1 from ev where ev.venture_id = v.id and ev.rank >= 2))
      ))
  )
  select id, name, sector, stage, country, description, full_name, city, duration_seconds, last_activity,
    updates_90d, areas, count(*) over ()
  from matched
  order by lower(name), id
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
$$;

-- ---------------------------------------------------------------------------
-- Introductions. An approved investor asks with a short note, the founder
-- accepts or declines, and an accepted request opens a conversation.
-- The names are copied onto the request when it is made, so each side sees
-- who asked without reading the other's profile.
-- ---------------------------------------------------------------------------
create type public.introduction_status as enum ('pending', 'accepted', 'declined', 'withdrawn');

create table public.introductions (
  id uuid primary key default gen_random_uuid(),
  venture_id uuid not null references public.ventures (id) on delete cascade,
  founder_id uuid not null references auth.users (id) on delete cascade,
  investor_id uuid not null references auth.users (id) on delete cascade,
  note text not null check (char_length(note) between 20 and 600),
  status public.introduction_status not null default 'pending',
  investor_name text not null,
  investor_type text not null,
  investor_firm text,
  venture_name text not null,
  founder_name text not null,
  created_at timestamptz not null default now(),
  decided_at timestamptz
);
-- One open or answered request per investor and venture. A declined request
-- is final, so a founder is not asked twice by the same investor. A request
-- the investor withdrew can be made again.
create unique index introductions_once on public.introductions (investor_id, venture_id)
  where status in ('pending', 'accepted', 'declined');
create index introductions_founder_idx on public.introductions (founder_id, created_at desc);
create index introductions_investor_idx on public.introductions (investor_id, created_at desc);
alter table public.introductions enable row level security;

create policy "introductions: the two people involved, and staff, read" on public.introductions
  for select using (auth.uid() in (founder_id, investor_id) or public.is_staff());
create policy "introductions: approved investors request" on public.introductions
  for insert with check (investor_id = auth.uid() and public.is_approved_investor());
create policy "introductions: the two people involved answer" on public.introductions
  for update using (auth.uid() in (founder_id, investor_id));

create or replace function public.prepare_introduction() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v public.ventures;
  inv public.profiles;
  ip public.investor_profiles;
  f public.profiles;
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
  -- Ten requests a day per investor, so no founder is flooded by one person.
  if (select count(*) from public.introductions
      where investor_id = auth.uid() and created_at > now() - interval '1 day') >= 10 then
    raise exception 'you have reached the limit of ten requests a day' using errcode = 'P0001';
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
create trigger introductions_prepare before insert on public.introductions
  for each row execute function public.prepare_introduction();

-- Only the status moves, once, from pending. The founder accepts or
-- declines. The investor can withdraw a request the founder has not answered.
create or replace function public.guard_introduction_update() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (new.venture_id, new.founder_id, new.investor_id, new.note, new.investor_name, new.investor_type,
      new.investor_firm, new.venture_name, new.founder_name, new.created_at)
     is distinct from
     (old.venture_id, old.founder_id, old.investor_id, old.note, old.investor_name, old.investor_type,
      old.investor_firm, old.venture_name, old.founder_name, old.created_at) or new.id <> old.id then
    raise exception 'only the status of an introduction can change' using errcode = '42501';
  end if;
  if old.status <> 'pending' then
    raise exception 'this request has already been answered' using errcode = 'P0001';
  end if;
  if not ((auth.uid() = old.founder_id and new.status in ('accepted', 'declined'))
          or (auth.uid() = old.investor_id and new.status = 'withdrawn')) then
    raise exception 'that change is not allowed' using errcode = '42501';
  end if;
  new.decided_at := now();
  return new;
end;
$$;
create trigger introductions_guard_update before update on public.introductions
  for each row execute function public.guard_introduction_update();

-- Messages in an accepted introduction. Only the two people involved read
-- and write them. They cannot be edited or deleted.
create table public.introduction_messages (
  id bigint generated always as identity primary key,
  introduction_id uuid not null references public.introductions (id) on delete cascade,
  sender_id uuid not null references auth.users (id) on delete cascade,
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);
create index introduction_messages_idx on public.introduction_messages (introduction_id, created_at);
alter table public.introduction_messages enable row level security;
create policy "messages: the two people involved read" on public.introduction_messages
  for select using (exists (
    select 1 from public.introductions i
    where i.id = introduction_id and auth.uid() in (i.founder_id, i.investor_id)
  ));
create policy "messages: the two people involved write once accepted" on public.introduction_messages
  for insert with check (
    sender_id = auth.uid()
    and exists (
      select 1 from public.introductions i
      where i.id = introduction_id and i.status = 'accepted'
        and (auth.uid() = i.founder_id or (auth.uid() = i.investor_id and public.is_approved_investor()))
    )
  );
create trigger introduction_messages_append_only before update or delete on public.introduction_messages
  for each row execute function public.forbid_change();

-- ---------------------------------------------------------------------------
-- Rights. Visitors who are not signed in call none of the new functions.
-- ---------------------------------------------------------------------------
revoke execute on function public.is_approved_investor() from public, anon;
revoke execute on function public.venture_visible_to_investor(uuid) from public, anon;
revoke execute on function public.founder_visible_to_investor(text) from public, anon;
revoke execute on function public.decide_investor(uuid, boolean) from public, anon;
revoke execute on function public.venture_evidence(uuid) from public, anon;
revoke execute on function public.decide_evidence(uuid, text, public.evidence_lane, text, text, integer, integer, numeric, public.product_stage) from public, anon;
revoke execute on function public.record_score(uuid, integer, public.league, jsonb, text, uuid) from public, anon;
revoke execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) from public, anon;
revoke execute on function public.guard_publish() from public, anon;
revoke execute on function public.prepare_introduction() from public, anon;
revoke execute on function public.guard_introduction_update() from public, anon;
grant execute on function public.is_approved_investor() to authenticated;
grant execute on function public.venture_visible_to_investor(uuid) to authenticated;
grant execute on function public.founder_visible_to_investor(text) to authenticated;
grant execute on function public.decide_investor(uuid, boolean) to authenticated;
grant execute on function public.venture_evidence(uuid) to authenticated;
grant execute on function public.decide_evidence(uuid, text, public.evidence_lane, text, text, integer, integer, numeric, public.product_stage) to authenticated;
grant execute on function public.record_score(uuid, integer, public.league, jsonb, text, uuid) to authenticated;
grant execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) to authenticated;
revoke all on public.investor_profiles, public.pitches, public.venture_updates, public.introductions, public.introduction_messages from anon;
