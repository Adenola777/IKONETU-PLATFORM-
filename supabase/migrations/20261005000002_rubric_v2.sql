-- Generated from packages/score-engine/src/rubric.ts. Do not edit by hand.
-- Regenerate with: pnpm --filter @ikonetu/score-engine rubric:sql
insert into public.rubric_versions (version, is_active) values ('v2', true)
on conflict (version) do update set is_active = excluded.is_active;

insert into public.rubric_signals (rubric_version, code, category, label, mode, points, max_points, usd_per_point, stage_points) values
  ('v2', 'company_registration', 'identity', 'Company registration matched to the founder', 'fixed', 50, 50, null, null),
  ('v2', 'government_id', 'identity', 'Government ID verified', 'fixed', 30, 30, null, null),
  ('v2', 'operating_tenure', 'identity', 'Months operating', 'months', 1, 20, null, null),
  ('v2', 'tax_registration', 'legal', 'Tax registration', 'fixed', 50, 50, null, null),
  ('v2', 'legal_documents', 'legal', 'Legal documents such as IP filings, contracts or licences', 'per_item', 10, 50, null, null),
  ('v2', 'revenue', 'financial', 'Verified revenue, last 12 months', 'revenue', 1, 80, 100, null),
  ('v2', 'financial_records', 'financial', 'Months of verified financial records', 'months', 4, 40, null, null),
  ('v2', 'business_account', 'financial', 'Verified business bank or mobile money account', 'fixed', 50, 50, null, null),
  ('v2', 'financial_statements', 'financial', 'Verified financial statements', 'per_item', 10, 30, null, null),
  ('v2', 'product_stage', 'product', 'Product stage with evidence', 'stage', 0, 130, null, '{"idea":0,"mvp":50,"revenue":90,"scaling":130}'::jsonb),
  ('v2', 'customer_evidence', 'product', 'Customer evidence such as signed orders or usage data', 'per_item', 10, 70, null, null),
  ('v2', 'customer_interviews', 'market', 'Documented customer interviews', 'per_item', 5, 40, null, null),
  ('v2', 'pilot_letters', 'market', 'Signed pilot or intent letters', 'per_item', 10, 40, null, null),
  ('v2', 'market_research', 'market', 'Market research document', 'fixed', 20, 20, null, null),
  ('v2', 'team_members', 'team', 'Verified team members', 'per_item', 5, 40, null, null),
  ('v2', 'team_credentials', 'team', 'Verified team credentials', 'per_item', 15, 60, null, null),
  ('v2', 'student_status', 'team', 'Student or graduate status verified', 'fixed', 20, 20, null, null),
  ('v2', 'programme_completed', 'team', 'Recognised programme completed', 'per_item', 15, 30, null, null),
  ('v2', 'website_live', 'media', 'Live website, checked automatically', 'fixed', 20, 20, null, null),
  ('v2', 'social_profile', 'media', 'Verified social profile', 'fixed', 20, 20, null, null),
  ('v2', 'pitch_deck', 'media', 'One-pager or pitch deck', 'fixed', 20, 20, null, null),
  ('v2', 'press_coverage', 'media', 'Verified press coverage', 'per_item', 10, 40, null, null),
  ('v2', 'operational_evidence', 'operations', 'Operational evidence such as supplier contracts, premises or tools', 'per_item', 10, 50, null, null)
on conflict (rubric_version, code) do update set
  category = excluded.category, label = excluded.label, mode = excluded.mode, points = excluded.points,
  max_points = excluded.max_points, usd_per_point = excluded.usd_per_point, stage_points = excluded.stage_points;
