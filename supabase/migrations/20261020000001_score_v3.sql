-- The IkonetU Score, rubric v3, and the founder's view of it. 20 October 2026.
--
-- The owner adopted the Scoring System Specification of March 2026 (Exhibit 01-04) in place
-- of rubric v2 on 20 October 2026, and ruled the same day that:
--   * self-declared claims count at 0.60 of their points (rubric v2 gave them nothing),
--   * a reviewed statement or export may stand in for an API the specification names,
--   * a reviewer may judge where the specification would use AI,
--   * a reviewer's own check of a government registry counts as Tier 1,
--   * the countries stay Nigeria, Ghana and Kenya.
-- docs/DECISIONS.md records each choice. Founders now see their own score; investors still do
-- not, until stage 2.
--
-- This migration holds the tables and functions. 20261020000002_rubric_v3.sql seeds the
-- rubric from service/app/score_engine/rubric.py and makes it the active one.
--
-- 1. rubric_categories holds each category's maximum, weight and pathway.
-- 2. rubric_signals gains how a founder shows each signal today, and what to send.
-- 3. score_snapshots keeps one score per venture per month. A month's row changes only while
--    that month lasts, so every past month stays as it was (specification, page 29).
-- 4. record_score() writes the month's snapshot, accepts the server's own service role as well
--    as staff, and refuses a staff member's own venture, as decide_evidence() does.
-- 5. declare_evidence() lets an active founder state a self-declared signal, which counts at
--    once at the self-declared weight without a review.

-- ---------------------------------------------------------------- 1. categories
create table public.rubric_categories (
  rubric_version text not null references public.rubric_versions (version),
  code text not null,
  label text not null check (char_length(label) between 1 and 80),
  max_points integer not null check (max_points > 0),
  weight integer not null check (weight between 1 and 100),
  alternative_to text,
  position integer not null,
  primary key (rubric_version, code)
);
alter table public.rubric_categories enable row level security;
create policy "rubric categories: readable" on public.rubric_categories for select using (true);
revoke all on public.rubric_categories from anon, authenticated;
grant select on public.rubric_categories to anon, authenticated;

-- ---------------------------------------------------------------- 2. how each signal is shown
alter table public.rubric_signals
  add column how text check (how is null or how in ('reviewer', 'statement', 'judgement', 'link', 'self', 'later')),
  add column hint text check (hint is null or char_length(hint) <= 200);

-- ---------------------------------------------------------------- 3. the monthly record
create table public.score_snapshots (
  venture_id uuid not null references public.ventures (id) on delete cascade,
  month date not null check (month = date_trunc('month', month)::date),
  total integer not null check (total between 0 and 1000),
  league public.league not null,
  categories jsonb not null,
  tiers jsonb not null default '{}'::jsonb,
  rubric_version text not null,
  recorded_at timestamptz not null default now(),
  primary key (venture_id, month)
);
create index score_snapshots_month_idx on public.score_snapshots (month);
alter table public.score_snapshots enable row level security;
create policy "score snapshots: founder reads own, staff read all" on public.score_snapshots
  for select using (public.owns_venture(venture_id) or public.is_staff());
revoke all on public.score_snapshots from anon, authenticated;
grant select on public.score_snapshots to authenticated;

-- A row for a month that has ended never changes. Deleting stays possible, because a deleted
-- venture takes its rows with it, and no policy lets a signed-in user delete one.
create or replace function public.freeze_past_snapshots() returns trigger
language plpgsql set search_path = '' as $$
begin
  if old.month < date_trunc('month', now() at time zone 'utc')::date then
    raise exception 'the score record for a month that has ended cannot change' using errcode = '42501';
  end if;
  if new.venture_id <> old.venture_id or new.month <> old.month then
    raise exception 'a score record cannot move to another venture or month' using errcode = '42501';
  end if;
  return new;
end;
$$;
create trigger score_snapshots_freeze before update on public.score_snapshots
  for each row execute function public.freeze_past_snapshots();
revoke execute on function public.freeze_past_snapshots() from public, anon, authenticated;

-- ---------------------------------------------------------------- 4. recording a score
drop function public.record_score(uuid, integer, public.league, jsonb, text, uuid);
create function public.record_score(
  p_venture uuid, p_total integer, p_league public.league, p_categories jsonb, p_rubric text,
  p_cause uuid default null, p_tiers jsonb default null
) returns void
language plpgsql security definer set search_path = public as $$
declare
  old_total integer;
  this_month date := date_trunc('month', now() at time zone 'utc')::date;
begin
  if not (public.is_staff() or auth.role() = 'service_role') then
    raise exception 'only reviewers, admins and the server can record a score' using errcode = '42501';
  end if;
  if exists (select 1 from public.ventures v where v.id = p_venture and v.founder_id = auth.uid()) then
    raise exception 'nobody can record the score of their own venture' using errcode = '42501';
  end if;
  insert into public.score_snapshots (venture_id, month, total, league, categories, tiers, rubric_version, recorded_at)
  values (p_venture, this_month, p_total, p_league, p_categories, coalesce(p_tiers, '{}'::jsonb), p_rubric, now())
  on conflict (venture_id, month) do update set
    total = excluded.total, league = excluded.league, categories = excluded.categories, tiers = excluded.tiers,
    rubric_version = excluded.rubric_version, recorded_at = excluded.recorded_at;
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
revoke execute on function public.record_score(uuid, integer, public.league, jsonb, text, uuid, jsonb) from public, anon;
grant execute on function public.record_score(uuid, integer, public.league, jsonb, text, uuid, jsonb) to authenticated, service_role;

-- ---------------------------------------------------------------- 5. self-declared signals
-- The founder's own statement, for a signal the active rubric marks as self-declared. It is
-- approved at once in the self lane, so it counts at the self-declared weight. It is never
-- shown to investors, because venture_evidence() leaves the self lane out.
create or replace function public.declare_evidence(
  p_venture uuid, p_signal text, p_summary text, p_request_key uuid default null
) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  new_id uuid;
  said text := btrim(coalesce(p_summary, ''));
begin
  if not public.owns_venture(p_venture) then
    raise exception 'only the venture''s founder can make a statement for it' using errcode = '42501';
  end if;
  if not exists (
    select 1 from public.rubric_signals s
    join public.rubric_versions rv on rv.version = s.rubric_version and rv.is_active
    where s.code = p_signal and s.how = 'self'
  ) then
    raise exception 'that signal needs evidence a reviewer checks' using errcode = '22023';
  end if;
  if char_length(said) < 10 or char_length(said) > 280 then
    raise exception 'a statement is 10 to 280 characters' using errcode = '22023';
  end if;
  insert into public.evidence (venture_id, signal_code, summary, status, lane, decided_at, request_key)
  values (p_venture, p_signal, said, 'approved', 'self', now(), p_request_key)
  returning id into new_id;
  return new_id;
end;
$$;
revoke execute on function public.declare_evidence(uuid, text, text, uuid) from public, anon;
grant execute on function public.declare_evidence(uuid, text, text, uuid) to authenticated;
