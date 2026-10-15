-- ---------------------------------------------------------------------------
-- The founder's ask: how much the founder is raising and what for, in their
-- own words, for example "$150,000 to reach 5,000 paying merchants". It is
-- optional. Investors see it on the profile and on the discovery card.
-- The owner chose on 15 October 2026 to add it to the app, because the
-- website's sample profile shows one.
-- ---------------------------------------------------------------------------
alter table public.ventures add column ask text check (ask is null or char_length(ask) between 5 and 160);

-- discover_ventures() now returns the ask as well. A function's result
-- columns cannot change in place, so it is dropped and created again with
-- the same rules as in 20261015000002, and its rights are set again.
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
    select v.id, v.name, v.sector, v.stage, v.country, v.description, v.ask, p.full_name, p.city,
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
  select id, name, sector, stage, country, description, ask, full_name, city, duration_seconds, last_activity,
    updates_90d, areas, count(*) over ()
  from matched
  order by lower(name), id
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
$$;

revoke execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) from public, anon;
grant execute on function public.discover_ventures(text[], public.product_stage[], public.country_code[], text[], integer, integer, integer) to authenticated;
