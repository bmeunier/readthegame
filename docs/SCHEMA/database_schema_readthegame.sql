create table if not exists episodes (
  guid uuid primary key,
  title text not null,
  publish_date timestamptz,
  audio_url text not null,
  duration_sec integer,
  summary text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists speakers (
  id uuid primary key,
  label text not null,
  external_id text,
  created_at timestamptz default now()
);

create table if not exists transcripts (
  id uuid primary key,
  episode_guid uuid not null references episodes(guid) on delete cascade,
  created_at timestamptz default now()
);

create table if not exists utterances (
  id bigserial primary key,
  transcript_id uuid not null references transcripts(id) on delete cascade,
  start_sec numeric not null,
  end_sec numeric not null,
  text text not null,
  speaker_label text not null,
  confidence numeric
);

create index if not exists idx_transcripts_episode on transcripts(episode_guid);
create index if not exists idx_utterances_transcript on utterances(transcript_id);
create index if not exists idx_utterances_seek on utterances(transcript_id, start_sec);
