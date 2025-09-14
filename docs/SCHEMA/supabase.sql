-- docs/SCHEMA/supabase.sql
-- Read The Game — Supabase schema (Postgres + pgvector)
-- Safe to run multiple times.

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pg_trgm";
create extension if not exists "vector";

-- =========================
-- Tables
-- =========================

-- Episodes master record
create table if not exists public.episodes (
  id uuid primary key default uuid_generate_v4(),
  guid text unique,                       -- normalized GUID from RSS (optional)
  title text not null,
  publish_date timestamptz,
  audio_uri text,                         -- remote or storage URI
  duration_seconds integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Speakers catalog (global identities)
create table if not exists public.speakers (
  id text primary key,                    -- e.g., 'alex_hormozi'
  display_name text,                      -- human-friendly
  aliases text[] default '{}',            -- ["Alex", "alex"]
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Episode segments (aligned diarization + ASR)
-- Optional: embedding for semantic search
create table if not exists public.segments (
  id bigserial primary key,
  episode_id uuid not null references public.episodes(id) on delete cascade,
  start_seconds double precision not null,
  end_seconds double precision not null,
  speaker_global_id text references public.speakers(id),
  text text not null,
  confidence real,                        -- optional ASR confidence
  embedding vector(768),                  -- optional; adjust dim to your model
  created_at timestamptz not null default now()
);

-- JSON artifacts per episode (canonical transcript, reports)
create table if not exists public.artifacts (
  id bigserial primary key,
  episode_id uuid not null references public.episodes(id) on delete cascade,
  kind text not null,                     -- e.g., 'transcript.json', 'validation_report.md'
  storage_uri text not null,              -- Supabase Storage or S3 URI
  checksum text,                          -- optional integrity check
  created_at timestamptz not null default now()
);

-- =========================
-- Indexes
-- =========================
-- Episodes lookup
create index if not exists idx_episodes_guid on public.episodes using btree(guid);
create index if not exists idx_episodes_publish_date on public.episodes(publish_date);

-- Segments time lookup and full-text helpers
create index if not exists idx_segments_episode_time on public.segments(episode_id, start_seconds, end_seconds);
create index if not exists idx_segments_speaker on public.segments(speaker_global_id);
create index if not exists idx_segments_text_trgm on public.segments using gin (text gin_trgm_ops);

-- Embedding ANN index (if embeddings are used)
-- For pgvector IVF/flat, you can also consider HNSW with pgvector>=0.6
-- Example IVF:
-- create index if not exists idx_segments_embedding on public.segments using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Artifacts
create index if not exists idx_artifacts_episode_kind on public.artifacts(episode_id, kind);

-- =========================
-- Triggers
-- =========================
create or replace function public.tg_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists trg_episodes_updated on public.episodes;
create trigger trg_episodes_updated before update on public.episodes
for each row execute function public.tg_updated_at();

drop trigger if exists trg_speakers_updated on public.speakers;
create trigger trg_speakers_updated before update on public.speakers
for each row execute function public.tg_updated_at();

-- =========================
-- Security (basic)
-- =========================
-- Adjust RLS to your needs; default here is open for simplicity.
alter table public.episodes disable row level security;
alter table public.speakers disable row level security;
alter table public.segments disable row level security;
alter table public.artifacts disable row level security;

-- =========================
-- Convenience Views
-- =========================
create or replace view public.v_episode_segments as
select
  e.id as episode_id,
  e.title,
  s.start_seconds,
  s.end_seconds,
  s.speaker_global_id,
  s.text,
  s.confidence
from public.episodes e
join public.segments s on s.episode_id = e.id
order by e.publish_date nulls last, s.start_seconds;

-- =========================
-- Seed (optional)
-- =========================
-- insert into public.speakers (id, display_name, aliases) values
--   ('alex_hormozi', 'Alex Hormozi', '{Alex,Alex H.}')
-- on conflict (id) do nothing;