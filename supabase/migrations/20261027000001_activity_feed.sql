-- ---------------------------------------------------------------------------
-- The activity feed. Written 27 October 2026.
--
-- The owner chose on 27 October 2026 that founders and approved investors
-- share one live feed of progress, that the system writes it as progress
-- happens instead of founders posting updates, that an entry names the
-- venture and describes the investor by type only, and that every published
-- venture appears, with no way to opt out. docs/DECISIONS.md records each
-- choice.
--
-- 1. activity_events holds one row for each step of progress. Triggers write
--    it; nobody writes or reads it directly. A row records:
--      published              the venture's profile was published for the first time
--      pitch_added            a pitch was added
--      pitch_replaced         the pitch was replaced with a new video
--      evidence_approved      a piece of evidence was approved in a lane that
--                             investors see (an outside source or a reviewer)
--      ask_set                the founder's ask was set or changed
--      introduction_accepted  the founder accepted an introduction
--    The rows hold no founder text: no ask, no summary, no note, no message,
--    and never the investor's name or firm. The IkonetU Score is never
--    recorded, because only the founder and staff see it.
-- 2. activity_feed() reads it for active founders, approved investors and
--    staff. It shows only ventures that are published now and whose founder
--    is active, so a hidden, unpublished or suspended founder's entries
--    leave the feed at once and come back if the profile is published again.
--    A founder also reads their own venture's entries, published or not, by
--    asking for that venture.
-- 3. Founders no longer post updates. The insert policy on venture_updates is
--    removed. The table and its rows stay; on 27 October 2026 production held
--    none.
-- 4. Discovery and the staff founders list count activity instead of posted
--    updates: active_weeks is the number of the last 13 weeks that hold an
--    entry, counted in UTC calendar days as the app's momentum strip counts
--    them, and last_activity includes the newest entry.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------- 1. the events
create type public.activity_kind as enum (
  'published', 'pitch_added', 'pitch_replaced', 'evidence_approved', 'ask_set', 'introduction_accepted'
);

create table public.activity_events (
  id bigint generated always as identity primary key,
  venture_id uuid not null references public.ventures (id) on delete cascade,
  kind public.activity_kind not null,
  detail jsonb not null default '{}'::jsonb,
  -- clock_timestamp(), so two entries written in one transaction keep their order.
  created_at timestamptz not null default clock_timestamp()
);
create index activity_events_created_idx on public.activity_events (created_at desc, id desc);
create index activity_events_venture_idx on public.activity_events (venture_id, created_at desc);
alter table public.activity_events enable row level security;
revoke all on public.activity_events from public, anon, authenticated;

-- An entry of the same kind for the same venture within a day is not written
-- again, so a founder who edits their ask or pitch several times in an
-- afternoon makes one entry.
create or replace function public.add_activity(p_venture uuid, p_kind public.activity_kind, p_detail jsonb default '{}'::jsonb)
returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_kind in ('ask_set', 'pitch_added', 'pitch_replaced') and exists (
    select 1 from public.activity_events
    where venture_id = p_venture and kind = p_kind and created_at > clock_timestamp() - interval '1 day'
  ) then
    return;
  end if;
  insert into public.activity_events (venture_id, kind, detail) values (p_venture, p_kind, coalesce(p_detail, '{}'::jsonb));
end;
$$;
revoke execute on function public.add_activity(uuid, public.activity_kind, jsonb) from public, anon, authenticated;

-- A venture is published for the first time, or its ask is set or changed.
-- Publishing again after a hold or after hiding it makes no new entry.
create or replace function public.ventures_activity() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.published_at is not null
     and (tg_op = 'INSERT' or old.published_at is null)
     and not exists (select 1 from public.activity_events where venture_id = new.id and kind = 'published') then
    perform public.add_activity(new.id, 'published');
  end if;
  if new.ask is not null and (tg_op = 'INSERT' or new.ask is distinct from old.ask) then
    perform public.add_activity(new.id, 'ask_set');
  end if;
  return null;
end;
$$;
create trigger ventures_activity after insert or update of published_at, ask on public.ventures
  for each row execute function public.ventures_activity();

-- A pitch is added, or replaced with a new video. A changed transcript alone
-- makes no entry.
create or replace function public.pitches_activity() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    perform public.add_activity(new.venture_id, 'pitch_added');
  elsif new.storage_path is distinct from old.storage_path then
    perform public.add_activity(new.venture_id, 'pitch_replaced');
  end if;
  return null;
end;
$$;
create trigger pitches_activity after insert or update of storage_path on public.pitches
  for each row execute function public.pitches_activity();

-- A piece of evidence is approved in a lane investors see: government or
-- source (an outside source backs it) or human or human_confirmed (an
-- IkonetU reviewer approved it), for a signal of the active rubric. These
-- are the rules by which venture_evidence() shows evidence. A statement the
-- founder makes alone, an approval by the automatic check alone, and
-- evidence for a signal the active rubric does not hold make no entry,
-- because investors do not see them.
create or replace function public.evidence_activity() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  shown text[] := array['government', 'source', 'human', 'human_confirmed'];
begin
  if new.status = 'approved' and new.lane::text = any (shown)
     and (tg_op = 'INSERT' or old.status <> 'approved' or not (old.lane::text = any (shown)))
     and exists (
       select 1 from public.rubric_signals s
       join public.rubric_versions rv on rv.version = s.rubric_version and rv.is_active
       where s.code = new.signal_code
     ) then
    perform public.add_activity(new.venture_id, 'evidence_approved', jsonb_build_object(
      'signal_code', new.signal_code,
      'outside', new.lane in ('government', 'source')
    ));
  end if;
  return null;
end;
$$;
create trigger evidence_activity after insert or update of status, lane on public.evidence
  for each row execute function public.evidence_activity();

-- The founder accepts an introduction. The entry keeps the investor's type
-- only, never their name or firm.
create or replace function public.introductions_activity() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'accepted' and old.status <> 'accepted' then
    perform public.add_activity(new.venture_id, 'introduction_accepted',
      jsonb_build_object('investor_type', new.investor_type));
  end if;
  return null;
end;
$$;
create trigger introductions_activity after update of status on public.introductions
  for each row execute function public.introductions_activity();

revoke execute on function public.ventures_activity() from public, anon, authenticated;
revoke execute on function public.pitches_activity() from public, anon, authenticated;
revoke execute on function public.evidence_activity() from public, anon, authenticated;
revoke execute on function public.introductions_activity() from public, anon, authenticated;

-- ---------------------------------------------------------------- 2. reading the feed
-- Newest first. p_before reads the page after the oldest entry shown, and
-- p_after reads what is new since the newest one. p_venture limits it to one
-- venture: its founder and staff then read every entry of it, published or
-- not, and anyone else reads it only while it is published.
create or replace function public.activity_feed(
  p_before timestamptz default null,
  p_after timestamptz default null,
  p_venture uuid default null,
  p_limit integer default 30
)
returns table (
  id bigint, kind public.activity_kind, venture_id uuid, venture_name text, sector text,
  country public.country_code, detail jsonb, created_at timestamptz
)
language plpgsql stable security definer set search_path = public as $$
declare
  me uuid := auth.uid();
  my_role public.user_role := public.app_role();
begin
  if my_role is null or my_role not in ('founder', 'investor', 'reviewer', 'admin') then
    raise exception 'only founders, approved investors and staff can read the activity feed' using errcode = '42501';
  end if;
  return query
  select a.id, a.kind, v.id, v.name, v.sector, v.country, a.detail, a.created_at
  from public.activity_events a
  join public.ventures v on v.id = a.venture_id
  join public.profiles p on p.user_id = v.founder_id
  where (p_venture is null or a.venture_id = p_venture)
    and (
      (v.published_at is not null and p.role = 'founder' and p.status = 'active')
      or (p_venture is not null and (v.founder_id = me or public.is_staff()))
    )
    and (p_before is null or a.created_at < p_before)
    and (p_after is null or a.created_at > p_after)
  order by a.created_at desc, a.id desc
  limit least(greatest(coalesce(p_limit, 30), 1), 100);
end;
$$;
revoke execute on function public.activity_feed(timestamptz, timestamptz, uuid, integer) from public, anon;
grant execute on function public.activity_feed(timestamptz, timestamptz, uuid, integer) to authenticated;

-- ---------------------------------------------------------------- 3. no more posted updates
drop policy "updates: founder posts own" on public.venture_updates;

-- ---------------------------------------------------------------- 4. counting activity
-- discover_ventures() and admin_ventures() return active_weeks in place of
-- updates_90d. A function's result columns cannot change in place, so each is
-- dropped and created again with the same rules as before, and its rights
-- are set again.
drop function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer);

create function public.discover_ventures(
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
  description text, ask text, founder_name text, city text, pitch_seconds numeric, last_activity timestamptz,
  active_weeks integer, areas jsonb, total_count bigint
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
        (select max(ev.created_at) from ev where ev.venture_id = v.id),
        (select max(ae.created_at) from public.activity_events ae where ae.venture_id = v.id)
      ) as last_activity,
      (select count(distinct (((now() at time zone 'utc')::date - (ae.created_at at time zone 'utc')::date) / 7))::integer
         from public.activity_events ae
        where ae.venture_id = v.id
          and ((now() at time zone 'utc')::date - (ae.created_at at time zone 'utc')::date) between 0 and 90) as active_weeks
    from visible v
  ),
  matched as (
    select v.id, v.name, v.sector, v.stage, v.country, v.description, v.ask, p.full_name, p.city,
      pi.duration_seconds, a.last_activity, a.active_weeks, coalesce(ar.areas, '[]'::jsonb) as areas
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
  select id, name, sector, stage, country, description, ask, full_name, city, duration_seconds, last_activity,
    active_weeks, areas, count(*) over ()
  from matched
  order by lower(name), id
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
$$;

revoke execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) from public, anon;
grant execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) to authenticated;

drop function public.admin_ventures(text, text, integer, integer);

create function public.admin_ventures(
  p_search text default null, p_state text default 'all', p_limit integer default 50, p_offset integer default 0
)
returns table (
  venture_id uuid, name text, sector text, stage public.product_stage, country public.country_code,
  founder_id uuid, founder_name text, founder_status public.account_status, founder_role public.user_role,
  published_at timestamptz, hidden_at timestamptz, has_pitch boolean,
  evidence_total integer, evidence_waiting integer, evidence_reviewed integer,
  active_weeks integer, introductions integer, last_activity timestamptz, created_at timestamptz, total_count bigint
)
language plpgsql stable security definer set search_path = public as $$
declare
  q text := nullif(trim(coalesce(p_search, '')), '');
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can list ventures' using errcode = '42501';
  end if;
  return query
  select v.id, v.name, v.sector, v.stage, v.country, v.founder_id, p.full_name, p.status, p.role,
    v.published_at, v.hidden_at,
    exists (select 1 from public.pitches pi where pi.venture_id = v.id),
    (select count(*)::integer from public.evidence e where e.venture_id = v.id),
    (select count(*)::integer from public.evidence e where e.venture_id = v.id and e.status in ('submitted', 'checking', 'needs_review')),
    (select count(*)::integer from public.evidence e where e.venture_id = v.id and e.status = 'approved'),
    (select count(distinct (((now() at time zone 'utc')::date - (ae.created_at at time zone 'utc')::date) / 7))::integer
       from public.activity_events ae
      where ae.venture_id = v.id
        and ((now() at time zone 'utc')::date - (ae.created_at at time zone 'utc')::date) between 0 and 90),
    (select count(*)::integer from public.introductions i where i.venture_id = v.id),
    greatest(
      v.updated_at,
      (select max(u.created_at) from public.venture_updates u where u.venture_id = v.id),
      (select max(e.created_at) from public.evidence e where e.venture_id = v.id),
      (select pi.updated_at from public.pitches pi where pi.venture_id = v.id),
      (select max(ae.created_at) from public.activity_events ae where ae.venture_id = v.id)
    ),
    v.created_at,
    count(*) over ()
  from public.ventures v
  join public.profiles p on p.user_id = v.founder_id
  where (q is null or v.name ilike '%' || q || '%' or p.full_name ilike '%' || q || '%')
    and case coalesce(p_state, 'all')
          when 'published' then v.published_at is not null
          when 'unpublished' then v.published_at is null and v.hidden_at is null
          when 'hidden' then v.hidden_at is not null
          else true
        end
  order by lower(v.name), v.id
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
end;
$$;

revoke execute on function public.admin_ventures(text, text, integer, integer) from public, anon;
grant execute on function public.admin_ventures(text, text, integer, integer) to authenticated;
