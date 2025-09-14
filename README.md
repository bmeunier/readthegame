# Read The Game

Turn podcasts into readable, speaker-aware transcripts with audio sync.

**Stack:**  
- **Inngest** — Orchestration of pipeline steps (durable, retries, cron, fan-out/fan-in)  
- **Deepgram** — Primary ASR (speech-to-text)  
- **pyannote Precision-2** — World-class speaker diarization (who spoke when)  
- **pyannote Speaker Platform** — Speaker memory (cross-episode speaker identification via voiceprints)  
- **Supabase** — Storage (Postgres + pgvector) and JSON artifacts  
- **Vercel** — Frontend deployment (episode pages)

---

## 🎯 Objective

Build a robust, speaker-aware, podcast ETL pipeline that processes episodes of *The Game* by Alex Hormozi into structured, searchable living documents — transcript, audio, segments, and metadata — enabling retrieval, analysis, and embedded insights.

---

## 🚀 Quickstart

```bash
# 1. Install dependencies
make setup-dev

# 2. Run API locally
uvicorn src.api:app --host 0.0.0.0 --port 8000

# 3. Run tests
pytest -q

# 4. Run Inngest Dev Server (from your web app project)
npx inngest-cli@latest dev
```

---

## ⚙️ Pipeline Overview

1. **RSS ingest**  
   - Fetch & normalize podcast metadata  
   - Validate audio URLs  
   - Skip reruns/throwbacks  

2. **Orchestration (Inngest)**  
   - Event-driven steps (`episode.new`, `episode.reprocess`)  
   - Retries, backoff, idempotency  
   - Fan-out/fan-in  
   - Cron for RSS polling  

3. **Audio processing**  
   - **Diarization:** pyannote Precision-2  
   - **ASR:** Deepgram primary (Whisper optional)  
   - **Speaker Memory:** pyannote Speaker Platform (identify/enroll voiceprints)  

4. **Storage & indexing**  
   - JSON artifacts saved to Supabase  
   - Structured data stored in Postgres + pgvector  

5. **Frontend**  
   - Vercel renders `/episodes/[id]` pages from Supabase or JSON  
   - Audio player + speaker-attributed transcript  

---

## 🧩 Example Transcript JSON

```json
{
  "episode_id": "ep-0123",
  "title": "How To Scale Without Burning Out",
  "segments": [
    {
      "start": 12.3,
      "end": 18.7,
      "speaker_id_global": "alex_hormozi",
      "text": "Here's why scaling feels overwhelming..."
    }
  ]
}
```

---

## 🔑 Environment

Set the following in `.env`:

```
DEEPGRAM_API_KEY=...
PYANNOTE_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
```

---

## 🧪 Testing

```bash
pytest -q
```

Tests cover:
- Diarization/ASR integration  
- Speaker memory (mocked API calls)  
- End-to-end episode ingestion  

---

## 📦 Deployment

- **Backend orchestration:** Inngest (functions + cron)  
- **Data:** Supabase (tables + pgvector + storage)  
- **Frontend:** Vercel (static/SSR pages)  

---

## 📌 Notes

- Whisper is optional and can be disabled if you only want to rely on Deepgram.
- A DIY x-vector speaker memory service may be added later if privacy or customization demands it, but the default path is pyannote Speaker Platform.  

---
