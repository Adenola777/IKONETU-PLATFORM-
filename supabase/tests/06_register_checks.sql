-- Checks for migration 20261024000001 (the investor register). Each check
-- prints PASS or FAIL with what it found. Run it after the migrations, as a
-- superuser, on its own or after 01 to 05. It makes its own people and its
-- own made-up register entries, and expects the register to start empty:
--   A  9d...0a  an admin             S  9d...0b  an admin who is then suspended
--   R  9d...0c  a reviewer           F  9d...0f  a founder
--   I  9d...12  an approved investor
\set ON_ERROR_STOP 1
reset role;

create or replace function pg_temp.ok(label text, passed boolean, detail text default '') returns void
language plpgsql as $$
begin
  if passed then raise notice 'PASS %', label; else raise notice 'FAIL % %', label, detail; end if;
end $$;

-- Refused calls are checked in a block, so a refusal does not stop the file.
create or replace function pg_temp.refused(label text, sql text, code text) returns void
language plpgsql as $$
begin
  execute sql;
  perform pg_temp.ok(label, false, 'call succeeded');
exception when others then
  perform pg_temp.ok(label, sqlstate = code, sqlstate || ' ' || sqlerrm);
end $$;

insert into auth.users (id, email) values
  ('9d000000-0000-0000-0000-00000000000a', 'ada@register.test'), ('9d000000-0000-0000-0000-00000000000b', 'sola@register.test'),
  ('9d000000-0000-0000-0000-00000000000c', 'rita@register.test'), ('9d000000-0000-0000-0000-00000000000f', 'fola@register.test'),
  ('9d000000-0000-0000-0000-000000000012', 'iyke@register.test');
insert into public.profiles (user_id, full_name, role, status) values
  ('9d000000-0000-0000-0000-00000000000a', 'Ada Admin', 'admin', 'active'),
  ('9d000000-0000-0000-0000-00000000000b', 'Sola Admin', 'admin', 'active'),
  ('9d000000-0000-0000-0000-00000000000c', 'Rita Reviewer', 'reviewer', 'active'),
  ('9d000000-0000-0000-0000-00000000000f', 'Fola Founder', 'founder', 'active'),
  ('9d000000-0000-0000-0000-000000000012', 'Iyke Investor', 'investor', 'active');

select pg_temp.ok('G0 the register starts empty', (select count(*) from public.investor_register) = 0);

set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- who may read and add
set request.jwt.claim.sub = '9d000000-0000-0000-0000-00000000000f';
select pg_temp.refused('G1 a founder cannot read the register', 'select * from public.admin_register()', '42501');
select pg_temp.refused('G2 a founder cannot read the months', 'select * from public.admin_register_months()', '42501');
select pg_temp.refused('G3 a founder cannot read the table directly', 'select * from public.investor_register', '42501');
select pg_temp.refused('G4 a founder cannot write to the table directly',
  $q$insert into public.investor_register (register_no, full_name, registered_on) values ('900', 'Some Body', '2026-07-01')$q$, '42501');

set request.jwt.claim.sub = '9d000000-0000-0000-0000-00000000000c';
select pg_temp.refused('G5 a reviewer cannot read the register', 'select * from public.admin_register()', '42501');
select pg_temp.refused('G6 a reviewer cannot add entries',
  $q$select * from public.admin_register_add('[{"register_no":"900","full_name":"Some Body","registered_on":"2026-07-01"}]')$q$, '42501');

set request.jwt.claim.sub = '9d000000-0000-0000-0000-000000000012';
select pg_temp.refused('G7 an approved investor cannot add entries',
  $q$select * from public.admin_register_add('[{"register_no":"900","full_name":"Some Body","registered_on":"2026-07-01"}]')$q$, '42501');

reset role;
set role anon;
set request.jwt.claim.role = 'anon';
set request.jwt.claim.sub = '';
select pg_temp.refused('G8 a visitor cannot call the register function', 'select * from public.admin_register()', '42501');
select pg_temp.refused('G9 a visitor cannot read the table', 'select * from public.investor_register', '42501');
reset role;
set role authenticated;
set request.jwt.claim.role = 'authenticated';

-- ---------------------------------------------------------------- adding
set request.jwt.claim.sub = '9d000000-0000-0000-0000-00000000000a';
select pg_temp.ok('G10 an admin adds three entries',
  (select (added, unchanged) = (3, 0) from public.admin_register_add($j$[
    {"register_no": "001", "full_name": "  Ada   Okafor ", "registered_on": "2026-07-01"},
    {"register_no": "002", "full_name": "Bayo Lawal", "registered_on": "2026-07-02"},
    {"register_no": "003", "full_name": "Chidi Eze", "registered_on": "2026-09-01"}]$j$)));
select pg_temp.ok('G11 spaces in a name are tidied',
  exists (select 1 from public.admin_register('001') where full_name = 'Ada Okafor' and registered_on = '2026-07-01'));
select pg_temp.ok('G12 the addition is in the audit log with its numbers',
  (select count(*) from public.audit_log where action = 'register.add' and actor_id = '9d000000-0000-0000-0000-00000000000a'
     and after = '{"added": 3, "unchanged": 0, "numbers": ["001", "002", "003"]}'::jsonb) = 1);
select pg_temp.ok('G13 the same list added again changes nothing',
  (select (added, unchanged) = (0, 3) from public.admin_register_add($j$[
    {"register_no": "001", "full_name": "Ada Okafor", "registered_on": "2026-07-01"},
    {"register_no": "002", "full_name": "Bayo Lawal", "registered_on": "2026-07-02"},
    {"register_no": "003", "full_name": "Chidi Eze", "registered_on": "2026-09-01"}]$j$)));
select pg_temp.ok('G14 adding nothing new writes no audit log entry',
  (select count(*) from public.audit_log where action = 'register.add' and actor_id = '9d000000-0000-0000-0000-00000000000a') = 1);

select pg_temp.refused('G15 a number already there with another name stops the whole addition',
  $q$select * from public.admin_register_add('[{"register_no":"004","full_name":"Dayo Ade","registered_on":"2026-08-01"},
     {"register_no":"002","full_name":"Bayo Lawal Jr","registered_on":"2026-07-02"}]')$q$, 'P0001');
select pg_temp.ok('G16 nothing from the stopped addition was kept',
  (select count(*) from public.admin_register()) = 3 and not exists (select 1 from public.admin_register('004')));
select pg_temp.refused('G17 a number already there with another date is refused',
  $q$select * from public.admin_register_add('[{"register_no":"003","full_name":"Chidi Eze","registered_on":"2026-09-02"}]')$q$, 'P0001');

select pg_temp.refused('G18 a date that does not exist is refused',
  $q$select * from public.admin_register_add('[{"register_no":"005","full_name":"Ema Obi","registered_on":"2026-02-30"}]')$q$, '22023');
select pg_temp.refused('G19 a date in another format is refused',
  $q$select * from public.admin_register_add('[{"register_no":"005","full_name":"Ema Obi","registered_on":"01/07/2026"}]')$q$, '22023');
select pg_temp.refused('G20 a date after today is refused',
  format($q$select * from public.admin_register_add('[{"register_no":"005","full_name":"Ema Obi","registered_on":"%s"}]')$q$,
         current_date + 1), '22023');
select pg_temp.refused('G21 a number given twice in one list is refused',
  $q$select * from public.admin_register_add('[{"register_no":"005","full_name":"Ema Obi","registered_on":"2026-08-02"},
     {"register_no":"005","full_name":"Femi Obi","registered_on":"2026-08-03"}]')$q$, '22023');
select pg_temp.refused('G22 a number of two digits is refused',
  $q$select * from public.admin_register_add('[{"register_no":"05","full_name":"Ema Obi","registered_on":"2026-08-02"}]')$q$, '22023');
select pg_temp.refused('G23 a name of one character is refused',
  $q$select * from public.admin_register_add('[{"register_no":"005","full_name":"E","registered_on":"2026-08-02"}]')$q$, '22023');
select pg_temp.refused('G24 an empty list is refused', $q$select * from public.admin_register_add('[]')$q$, '22023');
select pg_temp.refused('G25 something other than a list is refused',
  $q$select * from public.admin_register_add('{"register_no":"005"}')$q$, '22023');

-- ---------------------------------------------------------------- reading
select pg_temp.ok('G26 the months run from the first to the last, an empty month included, with running totals',
  (select array_agg(format('%s %s %s', to_char(month, 'YYYY-MM'), registered, running_total) order by month)
     from public.admin_register_months()) = array['2026-07 2 2', '2026-08 0 2', '2026-09 1 3']);
select pg_temp.ok('G27 the list is in register number order with the total',
  (select array_agg(register_no order by ord) from public.admin_register() with ordinality as t(register_no, full_name, registered_on, added_at, total_count, ord))
    = array['001', '002', '003']
  and (select max(total_count) from public.admin_register()) = 3);
select pg_temp.ok('G28 a search by part of a name finds the entry',
  (select array_agg(register_no) from public.admin_register('lawal')) = array['002']);
select pg_temp.ok('G29 a search by register number finds the entry',
  (select array_agg(register_no) from public.admin_register('003')) = array['003']);
select pg_temp.ok('G30 a month keeps the entries registered in it',
  (select array_agg(register_no order by register_no) from public.admin_register(null, '2026-07-15')) = array['001', '002']);
select pg_temp.ok('G31 a page holds the entries after the offset',
  (select array_agg(register_no) from public.admin_register(null, null, 1, 1)) = array['002']);

-- ---------------------------------------------------------------- a suspended admin
reset role;
update public.profiles set status = 'suspended' where user_id = '9d000000-0000-0000-0000-00000000000b';
set role authenticated;
set request.jwt.claim.sub = '9d000000-0000-0000-0000-00000000000b';
select pg_temp.refused('G32 a suspended admin cannot read the register', 'select * from public.admin_register()', '42501');
select pg_temp.refused('G33 a suspended admin cannot add entries',
  $q$select * from public.admin_register_add('[{"register_no":"900","full_name":"Some Body","registered_on":"2026-07-01"}]')$q$, '42501');

reset role;
select pg_temp.ok('G34 the register holds the three entries and nothing else', (select count(*) from public.investor_register) = 3
  and (select count(*) from public.investor_register where added_by = '9d000000-0000-0000-0000-00000000000a') = 3);
