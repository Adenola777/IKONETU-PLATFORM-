-- Approves the 92 pitch videos and links each to a founder record, as the owner asked on 27 October 2026:
-- the videos in the order the Videos page lists them, t01 to t92, go to the first 92 founder records that give a
-- startup name, in register order, which runs from p001 to p110. Each approval takes the founder's registration date,
-- as the owner ruled the same day, and the link's audit entry records both. It runs after the admin records are loaded, as the
-- admin named in admin_email: psql -v admin_email=<an admin's email> -f approve_and_link_videos.sql
-- Each approval goes through admin_pitch_video_decide(), which writes its own audit entry, and each link writes one.
-- It holds no personal data, only ids. Everything happens in one transaction, or nothing does.
-- It ran on a local copy of the database on 27 October 2026, where it approved, dated and linked the 92 videos.
-- It has not run on production, which holds none of these tables until migration 20261027000002 is applied.
\set ON_ERROR_STOP on
begin;
select set_config('request.jwt.claims', json_build_object('sub', u.id, 'role', 'authenticated')::text, true)
from auth.users u where lower(u.email::text) = lower(:'admin_email');

do $$
begin
  if not public.is_admin() then
    raise exception 'admin_email does not name an active admin';
  end if;
  if (select count(*) from public.pitch_video_files where status = 'pending' and record_id is null) <> 92
     or (select count(*) from public.pitch_video_files) <> 92 then
    raise exception 'expected 92 pitch videos, all pending and none linked';
  end if;
  if (select count(*) from public.founder_register where not sample and btrim(coalesce(startup, '')) <> '') < 92 then
    raise exception 'expected at least 92 founder records with a startup name';
  end if;
end $$;

do $$
declare
  v record;
begin
  for v in select video_id from public.pitch_video_files order by video_id loop
    perform public.admin_pitch_video_decide(v.video_id, 'approved',
      '{"problem": true, "solution": true, "market": true, "ask": true}'::jsonb);
  end loop;
end $$;

with v as (select video_id, decided_at, row_number() over (order by video_id) as n from public.pitch_video_files),
r as (select record_id, joined_at, row_number() over (order by char_length(record_id), record_id) as n
      from public.founder_register where not sample and btrim(coalesce(startup, '')) <> ''),
linked as (
  update public.pitch_video_files p set record_id = r.record_id, decided_at = r.joined_at
  from v join r using (n)
  where p.video_id = v.video_id
  returning p.video_id, p.record_id, v.decided_at as approved_at, p.decided_at
)
insert into public.audit_log (actor_id, action, entity, entity_id, before, after)
select auth.uid(), 'video.link', 'pitch_video_files', video_id, jsonb_build_object('record_id', null, 'decided_at', approved_at),
       jsonb_build_object('record_id', record_id, 'decided_at', decided_at)
from linked order by video_id;

do $$
begin
  if (select count(*) from public.pitch_video_files where status = 'approved' and record_id is not null) <> 92 then
    raise exception 'not every video is approved and linked';
  end if;
  if (select count(distinct record_id) from public.pitch_video_files) <> 92 then
    raise exception 'a founder record was linked twice';
  end if;
  if exists (select 1 from public.pitch_video_files p join public.founder_register f using (record_id)
             where p.decided_at <> f.joined_at) then
    raise exception 'an approval does not carry its founder''s registration date';
  end if;
end $$;
commit;
