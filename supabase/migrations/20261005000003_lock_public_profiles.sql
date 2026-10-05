-- Closes three gaps found by Supabase's security advisor after 0001 and 0002
-- were applied on 5 October 2026.
--
-- 1. public_profiles runs with its owner's rights, so it skips row level
--    security on profiles. Supabase's default privileges gave anon and
--    authenticated every right on it, which let a visitor who is not signed
--    in read, rename and delete founder profiles through the view. The view
--    is meant to be readable by signed-in users only.
revoke all on public.public_profiles from anon, authenticated;
grant select on public.public_profiles to authenticated;

-- 2. The security definer helpers are only for signed-in users and policies.
--    A visitor who is not signed in has no reason to call them over the API.
revoke execute on function public.app_role() from public, anon;
revoke execute on function public.is_staff() from public, anon;
revoke execute on function public.owns_venture(uuid) from public, anon;
revoke execute on function public.guard_profile_privileges() from public, anon;

-- 3. Fix the search path of the two trigger helpers. Neither reads a table.
alter function public.set_updated_at() set search_path = '';
alter function public.forbid_change() set search_path = '';
