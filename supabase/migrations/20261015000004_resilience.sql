-- Resilience fixes found by the engineering checklist review of 15 October 2026.
--
-- 1. Evidence and its files are saved in one transaction by submit_evidence(),
--    so a failure can no longer leave evidence without its files. A founder
--    may remove a file of their own that no evidence records, so the app can
--    clean up the files of a submission that failed. A recorded file stays.
-- 2. Evidence, progress updates and messages carry an optional request key.
--    A form sends the same key when it is sent twice, and the unique indexes
--    below keep the second copy out.
-- 3. The limit of ten introduction requests a day takes a lock per investor
--    before it counts, so simultaneous requests can no longer pass it. Two
--    simultaneous requests at nine made eleven before this change.
-- 4. health() lets an uptime monitor check that the database answers.
-- 5. ventures_with_stale_scores() lists ventures whose latest evidence decision
--    is newer than their score, so staff can recompute a score whose update
--    failed after the decision was saved.

-- ---------------------------------------------------------------- 2. request keys
alter table public.evidence add column request_key uuid;
alter table public.venture_updates add column request_key uuid;
alter table public.introduction_messages add column request_key uuid;
create unique index evidence_request_key on public.evidence (venture_id, request_key) where request_key is not null;
create unique index venture_updates_request_key on public.venture_updates (venture_id, request_key) where request_key is not null;
create unique index introduction_messages_request_key on public.introduction_messages (introduction_id, request_key) where request_key is not null;

-- ---------------------------------------------------------------- 1. evidence in one transaction
-- Runs as the founder who calls it, so the row level security policies on
-- evidence and evidence_files decide each insert, exactly as before.
create or replace function public.submit_evidence(
  p_venture uuid, p_signal text, p_summary text, p_link text, p_request_key uuid, p_files jsonb default '[]'::jsonb
) returns uuid
language plpgsql security invoker set search_path = public as $$
declare
  new_id uuid;
begin
  insert into public.evidence (venture_id, signal_code, summary, source_ref, request_key)
  values (p_venture, p_signal, p_summary, p_link, p_request_key)
  returning id into new_id;
  insert into public.evidence_files (evidence_id, storage_path, sha256, mime_type, size_bytes)
  select new_id, f ->> 'storage_path', f ->> 'sha256', f ->> 'mime_type', (f ->> 'size_bytes')::integer
  from jsonb_array_elements(coalesce(p_files, '[]'::jsonb)) as f;
  return new_id;
end;
$$;
revoke execute on function public.submit_evidence(uuid, text, text, text, uuid, jsonb) from public, anon;
grant execute on function public.submit_evidence(uuid, text, text, text, uuid, jsonb) to authenticated;

create policy "evidence bucket: founder sees own unrecorded file" on storage.objects
  for select to authenticated
  using (bucket_id = 'evidence' and (storage.foldername(name))[1] = auth.uid()::text
         and not exists (select 1 from public.evidence_files f where f.storage_path = storage.objects.name));
create policy "evidence bucket: founder removes own unrecorded file" on storage.objects
  for delete to authenticated
  using (bucket_id = 'evidence' and (storage.foldername(name))[1] = auth.uid()::text
         and not exists (select 1 from public.evidence_files f where f.storage_path = storage.objects.name));

-- ---------------------------------------------------------------- 3. the daily limit under concurrency
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
  -- The lock makes a second simultaneous request from the same investor wait
  -- until the first commits, so its count includes the first.
  perform pg_advisory_xact_lock(hashtextextended('introductions:' || auth.uid()::text, 0));
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

-- ---------------------------------------------------------------- 4. health
-- Returns true when the database answers. It reads nothing.
create or replace function public.health() returns boolean
language sql stable security invoker set search_path = public as $$ select true $$;
revoke execute on function public.health() from public;
grant execute on function public.health() to anon, authenticated;

-- ---------------------------------------------------------------- 5. scores that missed an update
create or replace function public.ventures_with_stale_scores()
returns table (venture_id uuid, name text, last_decided_at timestamptz, scored_at timestamptz)
language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_staff() then
    raise exception 'only reviewers and admins can see scores' using errcode = '42501';
  end if;
  return query
    select v.id, v.name, d.last_decided_at, s.computed_at
    from public.ventures v
    join (select e.venture_id, max(e.decided_at) as last_decided_at
          from public.evidence e where e.decided_at is not null group by e.venture_id) d on d.venture_id = v.id
    left join public.scores s on s.venture_id = v.id
    where s.computed_at is null or s.computed_at < d.last_decided_at
    order by d.last_decided_at;
end;
$$;
revoke execute on function public.ventures_with_stale_scores() from public, anon;
grant execute on function public.ventures_with_stale_scores() to authenticated;
