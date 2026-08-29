-- Config for your agent
create table config (
  id uuid primary key default gen_random_uuid(),
  plan text not null default 'free', -- 'free' or 'paid'
  max_requests_per_day int not null default 6,
  max_requests_per_month int not null default 200,
  keywords jsonb not null default '["Software Engineer","Data Engineer","ML Engineer"]',
  locations jsonb not null default '["Lahore, Pakistan","Remote"]',
  min_score_threshold numeric not null default 70,
  updated_at timestamptz not null default now()
);

-- Single resume for now
create table resumes (
  id uuid primary key default gen_random_uuid(),
  file_path text not null,
  parsed_text text not null,
  skills jsonb, -- optional: ["Python","SQL","ML",...]
  created_at timestamptz not null default now()
);

-- Jobs discovered from JSearch
create table jobs (
  id uuid primary key default gen_random_uuid(),
  source text not null default 'jsearch',
  external_id text,
  title text not null,
  company text not null,
  location text,
  url text unique not null,
  jd_text text,
  job_key_hash text unique not null,
  discovered_at timestamptz not null default now()
);

-- Match profiles between resume and jobs
create table match_profiles (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references jobs(id) on delete cascade,
  resume_id uuid not null references resumes(id) on delete cascade,
  overall_score numeric not null,
  semantic_score numeric,
  keyword_score numeric,
  skill_overlap jsonb,
  gap_analysis jsonb,
  created_at timestamptz not null default now()
);

-- Simple run logs
create table run_logs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  jobs_discovered int not null default 0,
  jobs_deduped_skipped int not null default 0,
  matches_computed int not null default 0,
  errors jsonb
);

-- Insert default config row
insert into config (id) values (gen_random_uuid());