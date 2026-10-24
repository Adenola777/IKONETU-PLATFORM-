-- ---------------------------------------------------------------------------
-- The investor register. Written 24 October 2026.
--
-- On 24 October 2026 the owner gave a register of investors kept outside the
-- app, with a register number, a name and a registration date for each, and
-- asked for it to be held in the database and managed from the admin pages.
-- The register given then covers July to September 2026.
--
-- 1. investor_register holds one row per register number. It holds a name and
--    a date only: no email address, no other contact detail, and no link to an
--    IkonetU account, because the register given has none.
-- 2. Only an admin reads or adds entries, through the functions below. The
--    table has no policy, so nobody reads or writes it directly.
-- 3. Entries are added in one transaction, all or none. An entry whose number
--    is already there with the same name and date is left as it is, so the
--    same list can be added twice. A number already there with a different
--    name or date stops the whole addition, so nothing is overwritten.
-- 4. Each addition writes one audit log entry with the numbers it added.
--
-- The names are personal data, so they are not in this file or anywhere else
-- in the repository. They reach the database through the admin page.
--
-- As written on 24 October 2026, this migration has been applied to a local
-- PostgreSQL 16 only, where supabase/tests/06_register_checks.sql passed.
-- ---------------------------------------------------------------------------

create table public.investor_register (
  register_no text primary key check (register_no ~ '^[0-9]{3,6}$'),
  full_name text not null check (char_length(full_name) between 2 and 120 and full_name = btrim(full_name)),
  registered_on date not null,
  added_at timestamptz not null default now(),
  added_by uuid references auth.users (id)
);
alter table public.investor_register enable row level security;
-- No policies: anon and authenticated users cannot read or write it.
revoke all on public.investor_register from anon, authenticated;

-- ---------------------------------------------------------------- adding entries
-- p_entries is a JSON array of {"register_no", "full_name", "registered_on"}.
-- The app checks each entry first; this checks every rule again.
create or replace function public.admin_register_add(p_entries jsonb)
returns table (added integer, unchanged integer)
language plpgsql security definer set search_path = public as $$
declare
  e jsonb;
  n integer := 0;
  v_no text;
  v_name text;
  v_day date;
  seen text[] := '{}';
  clashes text[] := '{}';
  new_nos text[] := '{}';
  new_names text[] := '{}';
  new_days date[] := '{}';
  same integer := 0;
  existing public.investor_register;
begin
  if not public.is_admin() then
    raise exception 'only admins can add to the investor register' using errcode = '42501';
  end if;
  if jsonb_typeof(p_entries) is distinct from 'array' or jsonb_array_length(p_entries) = 0 then
    raise exception 'give at least one entry' using errcode = '22023';
  end if;
  if jsonb_array_length(p_entries) > 1000 then
    raise exception 'add at most 1,000 entries at a time' using errcode = '22023';
  end if;
  -- Two additions at the same moment would each find the other's numbers missing.
  lock table public.investor_register in share row exclusive mode;

  for e in select value from jsonb_array_elements(p_entries) loop
    n := n + 1;
    v_no := btrim(coalesce(e ->> 'register_no', ''));
    v_name := btrim(regexp_replace(coalesce(e ->> 'full_name', ''), '\s+', ' ', 'g'));
    if v_no !~ '^[0-9]{3,6}$' then
      raise exception 'entry %: the register number must be 3 to 6 digits', n using errcode = '22023';
    end if;
    if char_length(v_name) not between 2 and 120 then
      raise exception 'entry %: the name must be 2 to 120 characters', n using errcode = '22023';
    end if;
    begin
      if coalesce(e ->> 'registered_on', '') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
        raise exception using errcode = '22007';
      end if;
      v_day := (e ->> 'registered_on')::date;
    exception when others then
      raise exception 'entry %: the registration date must be a real date written as 2026-07-01', n using errcode = '22023';
    end;
    if v_day > current_date then
      raise exception 'entry %: the registration date is after today', n using errcode = '22023';
    end if;
    if v_no = any (seen) then
      raise exception 'entry %: register number % is given twice', n, v_no using errcode = '22023';
    end if;
    seen := seen || v_no;

    select * into existing from public.investor_register r where r.register_no = v_no;
    if found then
      if existing.full_name = v_name and existing.registered_on = v_day then
        same := same + 1;
      else
        clashes := clashes || v_no;
      end if;
    else
      new_nos := new_nos || v_no;
      new_names := new_names || v_name;
      new_days := new_days || v_day;
    end if;
  end loop;

  if cardinality(clashes) > 0 then
    raise exception 'already in the register with a different name or date: %', array_to_string(clashes, ', ')
      using errcode = 'P0001';
  end if;

  insert into public.investor_register (register_no, full_name, registered_on, added_by)
  select b.reg_no, b.reg_name, b.reg_day, auth.uid() from unnest(new_nos, new_names, new_days) as b (reg_no, reg_name, reg_day);

  if cardinality(new_nos) > 0 then
    insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
    values (auth.uid(), 'register.add', 'investor_register', null, null,
            jsonb_build_object('added', cardinality(new_nos), 'unchanged', same, 'numbers', to_jsonb(new_nos)));
  end if;
  return query select cardinality(new_nos), same;
end;
$$;

-- ---------------------------------------------------------------- reading
-- Every entry in register number order. p_month, any day of a month, keeps the
-- entries registered in that month.
create or replace function public.admin_register(
  p_search text default null, p_month date default null, p_limit integer default 50, p_offset integer default 0
)
returns table (register_no text, full_name text, registered_on date, added_at timestamptz, total_count bigint)
language plpgsql stable security definer set search_path = public as $$
declare
  q text := nullif(btrim(coalesce(p_search, '')), '');
begin
  if not public.is_admin() then
    raise exception 'only admins can read the investor register' using errcode = '42501';
  end if;
  return query
  select r.register_no, r.full_name, r.registered_on, r.added_at, count(*) over ()
  from public.investor_register r
  where (q is null or r.full_name ilike '%' || q || '%' or r.register_no = q)
    and (p_month is null or date_trunc('month', r.registered_on) = date_trunc('month', p_month))
  order by char_length(r.register_no), r.register_no
  limit least(greatest(coalesce(p_limit, 50), 1), 100)
  offset greatest(coalesce(p_offset, 0), 0);
end;
$$;

-- Entries registered in each month, from the first month to the last, with the
-- running total. A month inside that span with no entries is listed with 0.
create or replace function public.admin_register_months()
returns table (month date, registered integer, running_total integer)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'only admins can read the investor register' using errcode = '42501';
  end if;
  return query
  with span as (
    select date_trunc('month', min(r.registered_on)) as first, date_trunc('month', max(r.registered_on)) as last
    from public.investor_register r
  ),
  months as (
    select m::date as month
    from span, generate_series(span.first, span.last, interval '1 month') m
  ),
  counted as (
    select months.month,
      (select count(*) from public.investor_register r where date_trunc('month', r.registered_on) = months.month)::integer as registered
    from months
  )
  select c.month, c.registered, (sum(c.registered) over (order by c.month))::integer
  from counted c
  order by c.month;
end;
$$;

-- ---------------------------------------------------------------- rights
revoke execute on function public.admin_register_add(jsonb) from public, anon;
revoke execute on function public.admin_register(text, date, integer, integer) from public, anon;
revoke execute on function public.admin_register_months() from public, anon;
grant execute on function public.admin_register_add(jsonb) to authenticated;
grant execute on function public.admin_register(text, date, integer, integer) to authenticated;
grant execute on function public.admin_register_months() to authenticated;
