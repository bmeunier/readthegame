# Inngest Function Map — Read The Game

This document defines the event-driven workflows orchestrated by Inngest for the Read The Game pipeline.

---

## 🎯 Core Events

- **`episode.new`**
  - Triggered when a new episode is discovered via RSS or manual input.
- **`episode.reprocess`**
  - Triggered manually to re-run the pipeline for an existing episode.
- **`speaker.identified`**
  - Internal event emitted after speaker memory step finishes.

---

## 🧩 Functions

### 1. `fetch_audio`
- **Trigger:** `episode.new`
- **Input:** `audio_url`, `episode_id`
- **Output Event:** `audio.fetched`
- **Notes:** Downloads and validates audio; saves reference to storage.

---

### 2. `diarize_episode`
- **Trigger:** `audio.fetched`
- **Action:** Call pyannote Precision-2 API
- **Output Event:** `episode.diarized`
- **Output Payload:** Speaker turns with timestamps

---

### 3. `transcribe_episode`
- **Trigger:** `episode.diarized`
- **Action:** Call Deepgram API (Whisper optional fallback)
- **Output Event:** `episode.transcribed`
- **Output Payload:** Transcript text with timestamps

---

### 4. `identify_speakers`
- **Trigger:** `episode.transcribed`
- **Action:** For each local speaker cluster, call pyannote Speaker Platform Identify/Enroll
- **Output Event:** `speaker.identified`
- **Output Payload:** Mapping of local speaker IDs → global speaker IDs

---

### 5. `index_episode`
- **Trigger:** `speaker.identified`
- **Action:** Store transcript JSON, metadata, and speaker IDs into Supabase (pgvector + storage)
- **Output Event:** `episode.processed`
- **Output Payload:** Episode record with transcript and global speaker mapping

---

## 🔁 Schedules

- **RSS Polling**
  - Cron: every 6 hours
  - Emits `episode.new` for newly discovered episodes

- **Backfills**
  - On demand, can replay old RSS entries or reprocess episodes

---

## 📌 Guarantees

- All functions use:
  - Retries with exponential backoff
  - Idempotency keys (episode_id + step)
  - Run history + replay (via Inngest UI)
- Fan-out/fan-in supported:
  - Speaker identification can run in parallel for each cluster
  - Results aggregated before `index_episode`

---

## ✅ Success Flow

`episode.new` → `fetch_audio` → `diarize_episode` → `transcribe_episode` → `identify_speakers` → `index_episode` → `episode.processed`

---