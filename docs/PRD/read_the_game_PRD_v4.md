# Read The Game — Product Requirements Document (PRD)
**Version:** 3.0  
**Date:** 2025-09-13  
**Project Lead:** Benoît Meunier  
**Scope:** Clean MVP focused on clarity, maintainability, and speaker-first podcast intelligence using pyannote Precision-2

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
             │
┌────────────▼────────────────┐
│     AUDIO INGESTION         │
├─────────────────────────────┤
│ • Download from URL         │
│ • (Fallback: Local file)    │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    DIARIZATION + ASR        │
├─────────────────────────────┤
│ • pyannote-audio (Precision-2) │
│ • Whisper local / Deepgram     │
│ • Optional confidence filtering │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│   SPEAKER MEMORY & LABELING │
├─────────────────────────────┤
│ • ECAPA embeddings           │
│ • Voiceprint storage         │
│ • Temporal boosting, drift   │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    INDEXING & STORAGE       │
├─────────────────────────────┤
│ • Supabase pgvector         │
│ • Future: Qdrant, Weaviate  │
└─────────────────────────────┘
```


## 🎯 Objective
Build a robust, speaker-aware, podcast ETL pipeline that processes episodes of "The Game" by Alex Hormozi into searchable, structured living documents — transcript, audio, segments, and metadata — enabling retrieval, analysis, and embedded insights.

---

## 🧠 Architecture Overview

```
┌─────────────────────────────┐
│     AUDIO INGESTION        │
├─────────────────────────────┤
│ • Local file (MP3/WAV)     │
│ • Future: RSS ingest       │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    DIARIZATION + ASR        │
├─────────────────────────────┤
│ • pyannote-audio (Precision-2) │
│ • Whisper local / Deepgram alt │
│ • Optional confidence filtering │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│   SPEAKER MEMORY & LABELING │
├─────────────────────────────┤
│ • ECAPA-based embeddings     │
│ • Voiceprint store (pgvector) │
│ • Cross-episode memory       │
│   - Guest clustering         │
│   - Temporal boosting        │
│   - Drift tracking           │
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    INDEXING & STORAGE       │
├─────────────────────────────┤
│ • Supabase pgvector         │
│ • Future: Qdrant, Weaviate  │
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
- ASR: Whisper (local) or Deepgram fallback
- Align transcript with speaker turns
- Output timestamped transcript with speaker IDs

### Confidence Filtering (Optional)
- Filter chunks below thresholds
  - ASR confidence < 0.85
  - ECAPA similarity < 0.75
- Generates report and mask file

### Speaker Memory
- ECAPA embeddings per segment (**required** for persistent, named speaker identification, e.g., "Alex Hormozi")
- Speaker profile:
```json
{
  "speaker_id": "alex",
  "embedding": [0.123, 0.987, ...],
  "confidence": 0.92,
  "quality": "high",
  "timestamp": "2025-09-13T10:00:00Z"
}
```
- Temporal boosting:
```python
adjusted_score = base_score * (1 / (1 + log1p(days_since_last)))
```
- Drift: cosine change over time per speaker

### Indexing & Storage
- Supabase pgvector (initial)
- Index by timestamp, speaker, confidence
- Future: switch to Qdrant

### Background Jobs
- Checkpointing at each stage
- Graceful exit on Ctrl+C
- Retry on fail
- Track via `job_state.json`

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
- Integrate ECAPA and test single speaker labeling
- ✅ Success: ECAPA pipeline + voiceprint output + orchestrator scaffold

### Phase 2: Core Pipeline
- Diarization + ASR processing with alignment
- Convert diarized audio to structured JSON with speaker labels
- ✅ Success: Full transcript JSON with speaker timestamps (1 episode)

### Phase 3: Speaker Intelligence
- Implement speaker memory, ECAPA matching across episodes
- Add temporal boosting and drift tracking logic
- ✅ Success: Persistent identity for speakers like "Alex Hormozi"

### Phase 4: Pipeline Reliability
- Build background job system with retry, checkpoint, resume
- Add report generation + confidence filtering logic
- ✅ Success: CLI-based job runner with test mode + Markdown summary

### Phase 5: Deployment — Fly.io
- Containerize ETL pipeline (Docker)
- Deploy on Fly.io with RSS polling + job queue
- Support `RSS_MODE=test` and `RSS_MODE=production`
- ✅ Success: JSON artifacts uploaded to GitHub or S3/CDN per episode

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
- `speaker_service.py`: ECAPA, pgvector logic
- `rss_processor.py`: Handles fetching and parsing RSS feeds, extracting episode metadata, audio URLs, and filtering rerun episodes based on configurable keywords.
- `guid_normalizer.py`: Handles inconsistent UUID formats from RSS feeds and database storage. Ensures all GUIDs are consistently formatted as 36-character UUIDs.

---

## 🔒 Risks & Mitigation

| Risk | Impact | Strategy |
|------|--------|----------|
| Pyannote license change | High | Snapshot working version |
| ECAPA fails on similar voices | Med | Add human override |
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

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation
- Setup env, define schemas, test ECAPA
- Success: 1 voiceprint → pgvector, basic orchestrator works

### Phase 2: Core Pipeline
- Transcript + Speaker Labeling Output
- Success: Transcribed JSON with ECAPA match

### Phase 3: Speaker Intelligence
- Temporal boost, drift, guest tracking
- Success: Voice memory maps across episodes

### Phase 4: Ready for Users
- CLI job runner, webhook, test report
- Success: Markdown report per job + retry flow

---

## 🚀 Deployment Strategy

### ⚙️ Pipeline Deployment (Fly.io)

The ETL pipeline, including audio processing, diarization, speaker memory, and RSS ingestion, will be deployed on **Fly.io**. Reasons:

- Low-latency performance with global regions
- Scalable background job runners for episodic processing
- Supports Python-based containers
- Easy to run distributed queues and background workers

#### Responsibilities on Fly.io:
- RSS fetch + episode queueing
- Diarization with pyannote
- Transcription with Whisper or Deepgram
- ECAPA-based speaker memory
- JSON output generation (`transcript.json` per episode)
- Markdown or report generation for validation
- Episode-level error logging and retry management

Each job run will generate:
- `transcript.json`
- `voiceprint.json` (optional metadata)
- `validation_report.md`

These artifacts can be inspected before batch processing all episodes.

---

### 🔄 Incremental Testing Pipeline (Fly.io)

A staging mechanism will be built into the RSS logic to allow per-episode validation:

- `RSS_MODE=test`: only one unprocessed episode is added to the job queue
- When episode is validated (visually or via test script), mark as "ready"
- When enough episodes are tested and approved, re-run the pipeline in batch mode

This allows validation of:
- Speaker attribution quality
- Transcript formatting
- Voiceprint continuity
- Playback + sync readiness

This supports a safe rollout over 900+ episodes.

---

### 🧑‍🎨 Frontend Deployment (Vercel)

The frontend layer — the HTML webpage per episode — will be hosted on **Vercel**. Reasons:

- Seamless static site generation (SSG) or server-side rendering (SSR)
- Great support for JSON-based data hydration
- Integrates with GitHub for previews
- Ideal for fast CDN delivery of rich transcript pages

#### Responsibilities on Vercel:
- Rendered episode pages (title, date, audio, speaker transcript)
- Uses data from processed `transcript.json` files
- Optional player-to-text sync integration
- Styling, theming, and UX for "Read The Game" brand

---

### 🔁 Deployment Flow Summary

1. 🛰️ Fly.io pulls RSS, processes episodes, emits JSON output
2. 📂 JSONs stored in durable storage or pushed to repo
3. 🎨 Vercel pulls processed JSON and builds episode pages
4. ✅ Team verifies new pages before full launch

```
        +------------------+
        |     RSS Feed     |
        +--------+---------+
                 |
                 v
        +--------▼---------+              +--------------------------+
        |     Fly.io       |              |     Developer Tools      |
        |  (Pipeline App)  |<-------------+  GitHub / CLI / Admin UI |
        +--------+---------+              +--------------------------+
                 |
         Generates JSON:
         - transcript.json
         - voiceprint.json
         - validation_report.md
                 |
                 v
        +--------▼---------+
        |    Storage /     |
        |  Repo / CDN Path |
        +--------+---------+
                 |
                 v
        +--------▼---------+
        |     Vercel       |
        |  (Frontend App)  |
        +------------------+
                 |
         Reads JSON to render:
         - Title
         - Audio player
         - Speaker transcript
```

---

## 📌 Strategic Product Requirements (SPRD) Additions

To support the split deployment model, the following additions are recommended in the SPRD:

### 🧱 Backend (Fly.io) Requirements

1. **Pipeline Runner App**
   - Dockerized app for RSS ingest, transcription, diarization, ECAPA matching
   - Support for:
     - RSS_MODE=test
     - RSS_MODE=production
   - Config-driven via `.env` or YAML

2. **Job Queue System**
   - Redis or lightweight async task runner
   - Ensures one-at-a-time test processing
   - Retry + checkpoint support

3. **Persistent Storage or Upload Pipeline**
   - Write `transcript.json`, `voiceprint.json`, and reports to:
     - GitHub repo (via token)
     - S3-compatible bucket
     - Or Vercel-compatible storage for frontend ingestion

4. **CLI / Admin Hooks**
   - For approving a test run, re-queuing episodes, or skipping

5. **Error Tracking & Logging**
   - Structured logs in JSON
   - Flags episodes with low confidence, drift, or speaker conflict

---

### 🎨 Frontend (Vercel) Requirements

1. **JSON Loader Layer**
   - Reads `transcript.json` and builds episode page
   - Error tolerance for incomplete data

2. **Episode Renderer**
   - Page layout:
     - Episode Title + Date
     - Audio Player (HTML5)
     - Speaker-attributed transcript (scrollable)

3. **Optional Sync**
   - Scroll to line while playing (if timestamped)

4. **Routing & Static Export**
   - Generates `/episodes/[episode_id].html` or similar
   - Supports previews via GitHub PR (Vercel integration)

---

### 🧪 Developer Workflow

- Fly.io deployment for ETL
- GitHub for code and JSON artifact storage
- Vercel builds from main branch JSON
- Manual validation before full ingestion

These additions ensure the team fully understands how the backend and frontend components interact, and can build toward a testable, scalable, maintainable system.
