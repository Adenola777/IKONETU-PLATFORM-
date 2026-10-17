-- ---------------------------------------------------------------------------
-- The admin dashboard. Written 17 October 2026.
--
-- The owner chose on 17 October 2026 to build an overview for staff, a list
-- of founders and ventures, a page for the audit log, and the management of
-- people and roles from the app instead of SQL. The owner also chose that an
-- admin may hide a published founder profile from investors, with a reason
-- the founder sees. docs/DECISIONS.md records each choice.
--
-- 1. A hold on a venture. An admin hides a profile with a reason, the
--    profile leaves investors' view at once, and the founder cannot publish
--    it again until an admin lifts the hold.
-- 2. A suspended founder can no longer write to their venture, publish it,
--    answer introductions or send messages. Suspending a founder also takes
--    their profile out of investors' view.
-- 3. Admins change a person's role or status through functions that refuse
--    a change to the admin's own account, and write each change to the
--    audit log with a reason.
-- 4. Read functions for the overview, the founders list and the people list.
--    The overview returns counts only. Nobody but the two people involved
--    reads the messages of an introduction, and none of these functions
--    reads them.
-- 5. The publish rule now also applies when a venture is created, so a
--    venture cannot be created already published without a pitch.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------- helpers
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(public.app_role() = 'admin', false);
$$;

-- ---------------------------------------------------------------- 1. the hold
alter table public.ventures add column hidden_at timestamptz;
alter table public.ventures add column hidden_reason text
  check (hidden_reason is null or char_length(hidden_reason) between 5 and 280);
alter table public.ventures add column hidden_by uuid references auth.users (id);
alter table public.ventures add constraint ventures_hold_complete check ((hidden_at is null) = (hidden_reason is null));

-- Replaces the rule of 20261015000002. A venture cannot be published while it
-- is held or without a pitch, and only an admin or the service role sets or
-- lifts a hold. It now runs when a venture is created as well as changed.
create or replace function public.guard_publish() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  was_published boolean := tg_op = 'UPDATE' and old.published_at is not null;
  hold_changed boolean := case when tg_op = 'INSERT'
    then new.hidden_at is not null or new.hidden_reason is not null or new.hidden_by is not null
    else (new.hidden_at, new.hidden_reason, new.hidden_by) is distinct from (old.hidden_at, old.hidden_reason, old.hidden_by) end;
begin
  if hold_changed and coalesce(auth.role(), '') <> 'service_role' and not public.is_admin() then
    raise exception 'only an admin can hide a profile or lift the hold' using errcode = '42501';
  end if;
  if new.published_at is not null and not was_published then
    if new.hidden_at is not null then
      raise exception 'IkonetU has hidden this profile from investors, and it cannot be published until an admin lifts the hold'
        using errcode = 'P0001';
    end if;
    if not exists (select 1 from public.pitches where venture_id = new.id) then
      raise exception 'add a pitch before publishing' using errcode = 'P0001';
    end if;
  end if;
  return new;
end;
$$;
drop trigger ventures_guard_publish on public.ventures;
create trigger ventures_guard_publish before insert or update on public.ventures
  for each row execute function public.guard_publish();

-- ---------------------------------------------------------------- 2. suspended founders
-- A founder owns a venture for these rules only while their account is an
-- active founder account. A suspended founder, or one whose role an admin
-- changed, reads and writes nothing through owns_venture().
create or replace function public.owns_venture(v uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.ventures vn
    join public.profiles p on p.user_id = vn.founder_id
    where vn.id = v and vn.founder_id = auth.uid() and p.role = 'founder' and p.status = 'active'
  );
$$;

drop policy "ventures: create own" on public.ventures;
create policy "ventures: active founders create own" on public.ventures
  for insert with check (founder_id = auth.uid() and public.app_role() = 'founder');
drop policy "ventures: update own" on public.ventures;
create policy "ventures: active founders update own" on public.ventures
  for update using (founder_id = auth.uid() and public.app_role() = 'founder')
  with check (founder_id = auth.uid());

drop policy "introductions: the two people involved answer" on public.introductions;
create policy "introductions: the two people involved answer" on public.introductions
  for update using ((auth.uid() = founder_id and public.app_role() = 'founder') or auth.uid() = investor_id);

drop policy "messages: the two people involved write once accepted" on public.introduction_messages;
create policy "messages: the two people involved write once accepted" on public.introduction_messages
  for insert with check (
    sender_id = auth.uid()
    and exists (
      select 1 from public.introductions i
      where i.id = introduction_id and i.status = 'accepted'
        and ((auth.uid() = i.founder_id and public.app_role() = 'founder')
             or (auth.uid() = i.investor_id and public.is_approved_investor()))
    )
  );

-- ---------------------------------------------------------------- 3. admin changes
-- An admin hides a venture's profile from investors, with a reason the
-- founder sees. The founder cannot publish it again until the hold is lifted.
create or replace function public.admin_hide_venture(p_venture uuid, p_reason text) returns void
language plpgsql security definer set search_path = public as $$
declare
  v public.ventures;
  reason text := left(trim(coalesce(p_reason, '')), 280);
begin
  if not public.is_admin() then
    raise exception 'only admins can hide a profile' using errcode = '42501';
  end if;
  if char_length(reason) < 5 then
    raise exception 'give the founder a reason' using errcode = '22023';
  end if;
  select * into v from public.ventures where id = p_venture for update;
  if not found then
    raise exception 'venture not found' using errcode = 'P0002';
  end if;
  if v.hidden_at is not null then
    raise exception 'this profile is already hidden' using errcode = 'P0001';
  end if;
  update public.ventures
     set published_at = null, hidden_at = now(), hidden_reason = reason, hidden_by = auth.uid()
   where id = p_venture;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'venture.hide', 'ventures', p_venture::text,
          jsonb_build_object('published_at', v.published_at),
          jsonb_build_object('published_at', null, 'reason', reason));
end;
$$;

-- Lifting the hold lets the founder publish again. It does not publish the
-- profile, because publishing stays the founder's choice.
create or replace function public.admin_lift_hold(p_venture uuid, p_note text default null) returns void
language plpgsql security definer set search_path = public as $$
declare
  v public.ventures;
  note text := nullif(left(trim(coalesce(p_note, '')), 280), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can lift a hold' using errcode = '42501';
  end if;
  select * into v from public.ventures where id = p_venture for update;
  if not found then
    raise exception 'venture not found' using errcode = 'P0002';
  end if;
  if v.hidden_at is null then
    raise exception 'this profile is not hidden' using errcode = 'P0001';
  end if;
  update public.ventures set hidden_at = null, hidden_reason = null, hidden_by = null where id = p_venture;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'venture.lift_hold', 'ventures', p_venture::text,
          jsonb_build_object('hidden_at', v.hidden_at, 'reason', v.hidden_reason),
          jsonb_build_object('hidden_at', null, 'note', note));
end;
$$;

-- An admin changes a person's role. Nobody changes their own role. A person
-- becomes a founder only if they own a venture, and an investor only if they
-- have an investor profile. A person who becomes staff stops being visible
-- to investors as a founder, so IkonetU staff have no profile in discovery.
-- Only investors wait for approval, so a waiting account given any other
-- role becomes active.
create or replace function public.admin_set_role(p_user uuid, p_role public.user_role, p_reason text default null) returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.profiles;
  after_row public.profiles;
  hidden integer := 0;
  reason text := nullif(left(trim(coalesce(p_reason, '')), 280), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can change a role' using errcode = '42501';
  end if;
  if p_user = auth.uid() then
    raise exception 'nobody can change their own role' using errcode = '42501';
  end if;
  if p_role not in ('founder', 'investor', 'reviewer', 'admin') then
    raise exception 'choose founder, investor, reviewer or admin' using errcode = '22023';
  end if;
  select * into before_row from public.profiles where user_id = p_user for update;
  if not found then
    raise exception 'person not found' using errcode = 'P0002';
  end if;
  if before_row.role = p_role then
    raise exception 'this person already has that role' using errcode = 'P0001';
  end if;
  if p_role = 'founder' and not exists (select 1 from public.ventures where founder_id = p_user) then
    raise exception 'this person has no venture, so they cannot be a founder' using errcode = 'P0001';
  end if;
  if p_role = 'investor' and not exists (select 1 from public.investor_profiles where user_id = p_user) then
    raise exception 'this person has no investor profile, so they cannot be an investor' using errcode = 'P0001';
  end if;
  update public.profiles
     set role = p_role,
         status = case when p_role <> 'investor' and status = 'pending' then 'active'::public.account_status else status end
   where user_id = p_user
  returning * into after_row;
  if p_role in ('reviewer', 'admin') then
    update public.ventures set published_at = null where founder_id = p_user and published_at is not null;
    get diagnostics hidden = row_count;
  end if;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), 'account.role', 'profiles', p_user::text,
          jsonb_build_object('role', before_row.role, 'status', before_row.status),
          jsonb_build_object('role', after_row.role, 'status', after_row.status, 'reason', reason, 'profiles_hidden', hidden));
end;
$$;

-- An admin suspends an account, with a reason, or makes it active again.
-- Nobody changes their own status. Suspending a founder takes their profile
-- out of investors' view, and making them active again does not publish it.
create or replace function public.admin_set_status(p_user uuid, p_status public.account_status, p_reason text default null) returns void
language plpgsql security definer set search_path = public as $$
declare
  before_row public.profiles;
  after_row public.profiles;
  hidden integer := 0;
  reason text := nullif(left(trim(coalesce(p_reason, '')), 280), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can change an account''s status' using errcode = '42501';
  end if;
  if p_user = auth.uid() then
    raise exception 'nobody can change their own status' using errcode = '42501';
  end if;
  if p_status not in ('active', 'suspended') then
    raise exception 'choose active or suspended' using errcode = '22023';
  end if;
  if p_status = 'suspended' and char_length(coalesce(reason, '')) < 5 then
    raise exception 'give a reason for the suspension' using errcode = '22023';
  end if;
  select * into before_row from public.profiles where user_id = p_user for update;
  if not found then
    raise exception 'person not found' using errcode = 'P0002';
  end if;
  if before_row.status = p_status then
    raise exception 'this account already has that status' using errcode = 'P0001';
  end if;
  update public.profiles set status = p_status where user_id = p_user returning * into after_row;
  if p_status = 'suspended' then
    update public.ventures set published_at = null where founder_id = p_user and published_at is not null;
    get diagnostics hidden = row_count;
  end if;
  insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
  values (auth.uid(), case when p_status = 'suspended' then 'account.suspend' else 'account.reactivate' end, 'profiles',
          p_user::text,
          jsonb_build_object('status', before_row.status),
          jsonb_build_object('status', after_row.status, 'reason', reason, 'profiles_hidden', hidden));
end;
$$;

-- ---------------------------------------------------------------- 4. reading
-- Reviewed evidence for the north star: approved by a reviewer or from an
-- outside source, the same lanes an investor sees as reviewed.
create or replace function public.admin_overview()
returns table (
  founders integer, ventures integer, ventures_published integer, ventures_hidden integer,
  investors_pending integer, investors_active integer, investors_suspended integer,
  staff integer, accounts_suspended integer,
  evidence_waiting integer, evidence_oldest_at timestamptz, scores_to_update integer,
  introductions_pending integer, introductions_30d integer, accepted_30d integer, declined_30d integer,
  north_star_30d integer, north_star_months jsonb,
  waitlist integer, investor_interest integer
)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can see the overview' using errcode = '42501';
  end if;
  return query
  with ns as (
    select i.decided_at
    from public.introductions i
    where i.status = 'accepted'
      and exists (
        select 1 from public.evidence e
        where e.venture_id = i.venture_id
          and e.status in ('approved', 'expired')
          and e.lane in ('government', 'source', 'human', 'human_confirmed')
          and e.decided_at <= i.created_at
      )
  ),
  months as (
    select m::date as month
    from generate_series(date_trunc('month', now()) - interval '5 months', date_trunc('month', now()), interval '1 month') m
  )
  select
    (select count(*)::integer from public.profiles where role = 'founder' and status = 'active'),
    (select count(*)::integer from public.ventures),
    (select count(*)::integer from public.ventures where published_at is not null),
    (select count(*)::integer from public.ventures where hidden_at is not null),
    (select count(*)::integer from public.profiles where role = 'investor' and status = 'pending'),
    (select count(*)::integer from public.profiles where role = 'investor' and status = 'active'),
    (select count(*)::integer from public.profiles where role = 'investor' and status = 'suspended'),
    (select count(*)::integer from public.profiles where role in ('reviewer', 'admin') and status = 'active'),
    (select count(*)::integer from public.profiles where status = 'suspended'),
    (select count(*)::integer from public.evidence where status in ('submitted', 'checking', 'needs_review')),
    (select min(created_at) from public.evidence where status in ('submitted', 'checking', 'needs_review')),
    (select count(*)::integer from public.ventures_with_stale_scores()),
    (select count(*)::integer from public.introductions where status = 'pending'),
    (select count(*)::integer from public.introductions where created_at > now() - interval '30 days'),
    (select count(*)::integer from public.introductions where status = 'accepted' and decided_at > now() - interval '30 days'),
    (select count(*)::integer from public.introductions where status = 'declined' and decided_at > now() - interval '30 days'),
    (select count(*)::integer from ns where ns.decided_at > now() - interval '30 days'),
    (select jsonb_agg(jsonb_build_object(
        'month', to_char(months.month, 'YYYY-MM'),
        'count', (select count(*) from ns where date_trunc('month', ns.decided_at) = months.month)) order by months.month)
     from months),
    (select count(*)::integer from public.waitlist),
    (select count(*)::integer from public.investor_interest);
end;
$$;

-- Every venture with its founder and what it holds, for staff. Sorted by
-- name. p_state takes 'all', 'published', 'unpublished' or 'hidden'.
create or replace function public.admin_ventures(
  p_search text default null, p_state text default 'all', p_limit integer default 50, p_offset integer default 0
)
returns table (
  venture_id uuid, name text, sector text, stage public.product_stage, country public.country_code,
  founder_id uuid, founder_name text, founder_status public.account_status, founder_role public.user_role,
  published_at timestamptz, hidden_at timestamptz, has_pitch boolean,
  evidence_total integer, evidence_waiting integer, evidence_reviewed integer,
  updates_90d integer, introductions integer, last_activity timestamptz, created_at timestamptz, total_count bigint
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
    (select count(*)::integer from public.venture_updates u where u.venture_id = v.id and u.created_at > now() - interval '90 days'),
    (select count(*)::integer from public.introductions i where i.venture_id = v.id),
    greatest(
      v.updated_at,
      (select max(u.created_at) from public.venture_updates u where u.venture_id = v.id),
      (select max(e.created_at) from public.evidence e where e.venture_id = v.id),
      (select pi.updated_at from public.pitches pi where pi.venture_id = v.id)
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

-- Every account with its email address and last sign-in, for admins only.
-- The email comes from Supabase Auth, which only this function reads.
-- p_user returns one account.
create or replace function public.admin_accounts(
  p_search text default null, p_role public.user_role default null, p_status public.account_status default null,
  p_limit integer default 50, p_offset integer default 0, p_user uuid default null
)
returns table (
  user_id uuid, full_name text, email text, role public.user_role, status public.account_status,
  created_at timestamptz, last_sign_in_at timestamptz, venture_id uuid, venture_name text, firm text, total_count bigint
)
language plpgsql stable security definer set search_path = public as $$
declare
  q text := nullif(trim(coalesce(p_search, '')), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can list accounts' using errcode = '42501';
  end if;
  return query
  select p.user_id, p.full_name, u.email::text, p.role, p.status, p.created_at, u.last_sign_in_at,
    fv.id, fv.name, ip.firm, count(*) over ()
  from public.profiles p
  join auth.users u on u.id = p.user_id
  left join lateral (
    select vn.id, vn.name from public.ventures vn where vn.founder_id = p.user_id order by vn.created_at limit 1
  ) fv on true
  left join public.investor_profiles ip on ip.user_id = p.user_id
  where (q is null or p.full_name ilike '%' || q || '%' or u.email::text ilike '%' || q || '%')
    and (p_user is null or p.user_id = p_user)
    and (p_role is null or p.role = p_role)
    and (p_status is null or p.status = p_status)
  order by p.created_at desc, p.user_id
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
end;
$$;

-- ---------------------------------------------------------------- rights
revoke execute on function public.is_admin() from public, anon;
revoke execute on function public.admin_hide_venture(uuid, text) from public, anon;
revoke execute on function public.admin_lift_hold(uuid, text) from public, anon;
revoke execute on function public.admin_set_role(uuid, public.user_role, text) from public, anon;
revoke execute on function public.admin_set_status(uuid, public.account_status, text) from public, anon;
revoke execute on function public.admin_overview() from public, anon;
revoke execute on function public.admin_ventures(text, text, integer, integer) from public, anon;
revoke execute on function public.admin_accounts(text, public.user_role, public.account_status, integer, integer, uuid) from public, anon;
grant execute on function public.is_admin() to authenticated;
grant execute on function public.admin_hide_venture(uuid, text) to authenticated;
grant execute on function public.admin_lift_hold(uuid, text) to authenticated;
grant execute on function public.admin_set_role(uuid, public.user_role, text) to authenticated;
grant execute on function public.admin_set_status(uuid, public.account_status, text) to authenticated;
grant execute on function public.admin_overview() to authenticated;
grant execute on function public.admin_ventures(text, text, integer, integer) to authenticated;
grant execute on function public.admin_accounts(text, public.user_role, public.account_status, integer, integer, uuid) to authenticated;
