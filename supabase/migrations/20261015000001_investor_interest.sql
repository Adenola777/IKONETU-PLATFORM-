-- ---------------------------------------------------------------------------
-- Investor interest, from the form at /investor-interest. Investor accounts are
-- not open yet, so this records who wants to hear when they open and what they
-- invest in. Written only by the API with the service role key, like the waitlist.
-- ---------------------------------------------------------------------------
create table public.investor_interest (
  id uuid primary key default gen_random_uuid(),
  full_name text not null check (char_length(full_name) between 2 and 120),
  email text not null check (char_length(email) between 5 and 160),
  country text not null check (country in ('NG', 'GH', 'KE', 'other')),
  firm text check (firm is null or char_length(firm) between 1 and 120),
  sectors text[] not null check (
    cardinality(sectors) between 1 and 5
    and sectors <@ array['Fintech', 'Agritech', 'Edtech', 'Health', 'Other']::text[]
  ),
  cheque_size text not null check (
    cheque_size in ('Under $25,000', '$25,000 to $100,000', '$100,000 to $500,000', 'Over $500,000', 'Prefer not to say')
  ),
  investor_type text not null check (investor_type in ('individual', 'angel', 'fund')),
  confirmed_adult boolean not null check (confirmed_adult),
  confirmed_statement boolean not null check (confirmed_statement),
  email_consent boolean not null check (email_consent),
  privacy_version text not null,
  source text,
  created_at timestamptz not null default now(),
  unique (email)
);
alter table public.investor_interest enable row level security;
-- No policies: anon and authenticated users cannot read or write it.
revoke all on public.investor_interest from anon, authenticated;
