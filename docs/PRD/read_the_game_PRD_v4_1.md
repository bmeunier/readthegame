# Read The Game — Product Requirements Document (PRD)
**Version:** 3.0  
**Date:** 2025-09-13  
**Project Lead:** Benoît Meunier  
**Scope:** Clean MVP focused on clarity, maintainability, and speaker-first podcast intelligence using pyannote Precision-2, pyannote Speaker Platform, Inngest orchestration, Deepgram ASR, and Supabase
---


---

## 🧠 Updated Architecture Diagram

```
┌─────────────────────────────┐
│     RSS INGESTION           │
├─────────────────────────────┤
│ • Fetch RSS/XML             │
│ • GUID normalization        │
│ • Audio URL validation      │
│ • Skip reruns/throwbacks    │
└────────────┬────────────────┘
             │  (event: episode.new)
┌────────────▼────────────────┐
│   ORCHESTRATION (Inngest)   │
├─────────────────────────────┤
│ • Event-driven steps        │
│ • Retries, backoff, idemp.  │
│ • Fan-out/fan-in            │
│ • Cron (RSS poll)           │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│        AUDIO FETCH          │
├─────────────────────────────┤
│ • Download from URL         │
│ • (Fallback: Local file)    │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    DIARIZATION (Precision-2)│
├─────────────────────────────┤
│ • Speaker turns & timestamps│
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│     ASR (Deepgram/Whisper)  │
├─────────────────────────────┤
│ • Transcript text           │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│ SPEAKER PLATFORM (pyannote) │
├─────────────────────────────┤
│ • Cross-episode ID mapping  │
│ • Enroll/identify voiceprints│
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    INDEXING & STORAGE       │
├─────────────────────────────┤
│ • Supabase (Postgres + vec) │
│ • JSON artifacts per ep.    │
└─────────────────────────────┘
```


## 🎯 Objective
Build a robust, speaker-aware, podcast ETL pipeline that processes episodes of "The Game" by Alex Hormozi into searchable, structured living documents — transcript, audio, segments, and metadata — enabling retrieval, analysis, and embedded insights.

---

## 🧠 Architecture Overview

```
┌─────────────────────────────┐
│     AUDIO / RSS INGEST     │
├─────────────────────────────┤
│ • Local file or RSS        │
└────────────┬────────────────┘
             │  (Inngest event)
┌────────────▼────────────────┐
│  ORCHESTRATION (Inngest)    │
├─────────────────────────────┤
│ • Steps, retries, parallel  │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  DIARIZATION (Precision-2)  │
├─────────────────────────────┤
│ • Who spoke when            │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│  ASR (Deepgram / Whisper)   │
├─────────────────────────────┤
│ • Words with timestamps     │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│ SPEAKER ID (pyannote SP)    │
├─────────────────────────────┤
│ • Global speaker identity   │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│   INDEXING & STORAGE        │
├─────────────────────────────┤
│ • Supabase pgvector         │
└─────────────────────────────┘
```

---

## 📦 Functional Requirements

### Audio Ingestion
- Accept local MP3/WAV
- Normalize metadata
- Future: RSS feed integration

### Diarization & Transcription
- Diarization: pyannote Precision-2
- ASR: Deepgram primary (Whisper optional)
- Align transcript with speaker turns
- Output timestamped transcript with speaker IDs

### Speaker Memory
- Use **pyannote Speaker Platform** for cross-episode identification ("speaker memory").
- For each local speaker cluster from Precision-2, create a representative snippet and call Identify/Enroll APIs.
- Store a stable `speaker_id_global` (e.g., "alex_hormozi") with similarity scores per turn.
- Support human overrides and aliasing ("alex", "Alex Hormozi" → "alex_hormozi").
- Optional heuristics:
  - Temporal boosting on recently seen speakers
  - Drift tracking via rolling cosine deltas

**Example: identification payload**
```json
{
  "episode_id": "ep-0123",
  "local_speaker": "B",
  "snippet": "s3://bucket/ep0123/spkB_00m30s_00m45s.wav"
}
```
**Result:**
```json
{
  "speaker_id_global": "alex_hormozi",
  "score": 0.94,
  "decision": "match"
}
```
**Note:** A DIY path using ECAPA/x-vectors on a self-hosted service remains a v2 option if cost, privacy, or customization demands it.

### Indexing & Storage
- Supabase pgvector (initial)
- Index by timestamp, speaker, confidence
- Future: switch to Qdrant

### Background Jobs
- Inngest-managed workflows with durable execution
- Per-stage retries with exponential backoff and idempotency
- Fan-out/fan-in for parallel segment processing
- Cron schedules for RSS polling and reprocessing
- Run history, logs, and replays for failed runs
- Local Dev Server for parity with production

---

## 🧪 Testing Plan

- Unit tests: diarization, ASR, ECAPA matcher
- Integration: episode full flow
- Performance: 1h audio < 90 mins
- QA: Ground truth episodes, manual overrides

---

## 📡 APIs (planned)

### Query API (REST)
- `GET /episodes/:id`  
  Returns full episode transcript data with speaker labels and timestamps.

---


## 🚀 Implementation Roadmap (Including Deployment)

### Phase 1: Foundation
- Setup development environment and repo structure
- Define schemas: `transcript.json`, `voiceprint.json`, episode metadata
- ✅ Success: Inngest project scaffold + function registry

### Phase 2: Core Pipeline
- Diarization + ASR processing with alignment
- Convert diarized audio to structured JSON with speaker labels
- ✅ Success: Full transcript JSON with speaker timestamps (1 episode)

### Phase 3: Speaker Intelligence
- Integrate pyannote Speaker Platform for cross-episode identification
- Add temporal boosting and drift tracking logic
- ✅ Success: Persistent identity for speakers like "Alex Hormozi"

### Phase 4: Pipeline Reliability
- Wire pipeline steps into Inngest (retries, checkpoints, resume)
- Add report generation + confidence filtering logic
- ✅ Success: CLI-based job runner with test mode + Markdown summary

### Phase 5: Orchestration & Storage
- Configure Inngest cron for RSS polling and backfills
- Persist artifacts to Supabase Storage or S3-compatible bucket
- ✅ Success: End-to-end run triggered by event → JSON artifacts saved

### Phase 6: Frontend Rendering — Vercel
- Static episode page generator (Astro or Next.js)
- Renders audio + transcript from `transcript.json`
- Supports `/episodes/[episode_id]` route + GitHub preview builds
- ✅ Success: Vercel shows beautiful "Read The Game" page per episode


## 📊 Success Metrics

- DER: < 15%
- WER: < 10%
- ECAPA match accuracy: 90%
- Speaker label correctness: high priority
- Time: < 1.5x realtime

---



---

## 🔗 RSS Feed Integration

### Overview
Enables automated podcast episode ingestion from standard RSS feeds with robust validation, GUID normalization, and error handling.

### Pipeline Stage: RSS Ingest

1. **RSS Fetch & Parse**
   - Uses `feedparser` to read XML feeds from `http/https` or `file://` sources.
   - Parses episode entries with iTunes extension support.

2. **Metadata Extraction**
   - Fields extracted:
     - `guid`: Unique episode identifier (critical for deduplication)
     - `title`: Cleaned and whitespace-trimmed
     - `publish_date`: RFC2822 or ISO format
     - `audio_url`: Direct link to media file
     - `episode_number`: Parsed from iTunes tags or regex (e.g., "Ep 42")
     - `description`: Episode summary
     - `duration`: Parsed into seconds (supports HH:MM:SS, MM:SS, plain seconds)

3. **GUID Normalization**
   - Supports:
     - Standard UUID (8-4-4-4-12)
     - Compact UUIDs (32-char)
     - Mixed-case and malformed versions
   - Converts all to canonical 36-char format
   - Case-insensitive
   - Invalid formats are skipped with warnings

4. **Audio URL Validation**
   - Ensures:
     - Valid schemes (`http`, `https`, `file`)
     - Audio MIME types or file extensions (`.mp3`, `.wav`, `.m4a`, etc.)
   - Skips entries with missing or non-audio URLs

5. **Rerun/Throwback Filtering**
   - Detects "rerun", "throwback", "replay", "best of" etc. in titles
   - Configurable keyword list
   - Case-insensitive match
   - Filter flag used for downstream skip logic

6. **Duration Parsing**
   - Accepts:
     - `itunes:duration` field
     - Format: HH:MM:SS, MM:SS, or plain seconds
   - Converts to integer seconds

7. **Error Handling & Logging**
   - Logs and skips entries without GUID or audio
   - Summarizes:
     - ✅ Episodes extracted
     - ⚠️ Episodes skipped (with reason)
     - ❌ Invalid GUIDs

8. **Processing Summary Report**
   - Metrics logged:
     - Count of episodes processed
     - Count skipped
     - Invalid GUID errors
   - Optional Markdown report generation

### Data Model: EpisodeMetadata

```json
{
  "guid": "e3d532d5-d216-4c26-a1c7-521efb2016c5",
  "title": "How To Scale Without Burning Out",
  "publish_date": "2023-05-14T08:00:00Z",
  "audio_url": "https://cdn.libsyn.com/ep123.mp3",
  "episode_number": 123,
  "description": "Alex explains the real reason...",
  "duration": 2145
}
```

### Key Properties

- 🔁 **Deduplication** via normalized GUIDs
- 🛡️ **Resilient**: Handles malformed entries gracefully
- 🧠 **Validated**: Ensures episode quality before pipeline entry
- 🧪 **Monitorable**: Summary logs for visibility
- ⚙️ **Configurable**: Filtering and regex logic adjustable



---

## 🛠️ RSS Ingestion Implementation Guide

### Step-by-Step Integration Plan

#### 1. Setup
- Add `feedparser` to requirements.
- Create module: `rss_processor.py`
- Create support module: `guid_normalizer.py`

#### 2. Fetch & Parse
- Input: RSS feed URL
- Use `feedparser.parse(url)`
- Loop through `feed.entries`

#### 3. Normalize & Validate
- Extract and normalize:
  - `guid`
  - `title`, `description`, `duration`
  - `audio_url`, `publish_date`
- Use helper from `guid_normalizer.py` for deduplication

#### 4. Filter Entries
- Use rerun filter:
```python
if is_rerun(title): continue
```
- Skip missing audio URLs:
```python
if not is_valid_audio_url(audio_url): continue
```

#### 5. Convert to Metadata Object
```python
EpisodeMetadata(
    guid=normalize_guid(...),
    title=...,
    audio_url=...,
    duration=parse_duration(...),
    episode_number=extract_ep_num(...),
    ...
)
```

#### 6. Output & Logging
- Store valid entries in list
- Log invalid/skipped ones
- Summary report:
```python
{
  "processed": 124,
  "skipped": 8,
  "invalid_guids": 3
}
```

#### 7. Connect to ETL Pipeline
- Pass `EpisodeMetadata` entries into the job queue
- Track GUIDs already processed to skip duplicates

---

### CLI Entry (Optional)
```bash
python ingest_rss.py --feed-url https://example.com/podcast.xml
```

---



## 📁 Appendix

- `enhanced_orchestrator.py`: Controls ETL flow
- `confidence_filter.py`: Optional mask generator
- `speaker_id_service.py`: pyannote Speaker Platform client and identity mapping
- `rss_processor.py`: Handles fetching and parsing RSS feeds, extracting episode metadata, audio URLs, and filtering rerun episodes based on configurable keywords.
- `guid_normalizer.py`: Handles inconsistent UUID formats from RSS feeds and database storage. Ensures all GUIDs are consistently formatted as 36-character UUIDs.

---

## 🔒 Risks & Mitigation

| Risk | Impact | Strategy |
|------|--------|----------|
| Pyannote license change | High | Snapshot working version |
| pyannote Speaker Platform mismatch | Med | Human override + alias table; adjust confidence thresholds |
| SaaS outage (ASR/pyannote/Inngest) | High | Graceful degradation, retries, cached artifacts |
| GPU cost spike | Med | Fallback to Deepgram |
| Speaker drift over time | Med | Track delta, retrain quarterly |
| GDPR data retention | High | Cleanup policy for voiceprints |

---

## 📝 Docs to Ship

- ✅ PRD (this)
- ✅ JSON schemas: episode, voiceprint
- ✅ transcript.json per episode as primary output
- ✅ Roadmap milestones
- ✅ Logs + report format
- 🟡 OpenAPI spec (next)
- 🟡 Deployment Dockerfile + envs
- ✅ Inngest function map (events, steps, retries)

---



### 🧪 Developer Workflow

- Inngest orchestration for ETL
- GitHub for code and JSON artifact storage
- Vercel builds from main branch JSON
- Manual validation before full ingestion

These additions ensure the team fully understands how the backend and frontend components interact, and can build toward a testable, scalable, maintainable system.