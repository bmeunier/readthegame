# CLAUDE.md

This document provides Claude with the necessary context, goals, and constraints to assist with the **Read The Game** project.

---

## 🎯 Project Goal

Turn Alex Hormozi's *The Game* podcast episodes into speaker-aware, structured, and searchable documents with transcripts, audio, and metadata. Enable reliable retrieval, analysis, and embedding into downstream systems.

---

## 🧠 Architecture Overview

**Stack:**
- **Inngest** — Orchestration of workflow steps (durable, retries, cron, fan-out/fan-in)
- **Deepgram** — Primary ASR (speech-to-text)
- **pyannote Precision-2** — Speaker diarization (who spoke when)
- **pyannote Speaker Platform** — Speaker memory (cross-episode speaker identification with voiceprints)
- **Supabase** — Postgres + pgvector for storage and JSON artifacts

**Flow:**
`episode.new` (event) → Inngest orchestrates steps → Diarization (Precision-2) → ASR (Deepgram) → Speaker Memory (pyannote Speaker Platform) → Supabase (storage + pgvector) → JSON + Markdown artifacts.

---

## 🛠️ Claude's Role

Claude is used to:
- Review PRDs and keep them aligned with the latest architecture decisions.  
- Suggest code refactors and consistency improvements.  
- Generate or update supporting documentation.  
- Maintain repo hygiene (naming conventions, dependency lists, tests).

---

## 🔄 Refactor Tasks Checklist

When asked to realign the repo, Claude should:

1. **Docs**
   - Ensure README.md matches current stack.
   - Keep PRDs synced with implementation decisions.
   - Remove any mention of ECAPA or Fly.io.

2. **Dependencies**
   - Core deps: fastapi, uvicorn, deepgram-sdk, supabase, sqlalchemy, feedparser, pydantic, pytest, ruff, black.
   - Optional ML deps (torch, torchaudio, pyannote.audio, speechbrain, whisper) moved to `requirements-ml-optional.txt` if local experimentation is desired.

3. **Speaker Memory**
   - Use `speaker_id_service.py` to connect to pyannote Speaker Platform APIs.
   - Functions: `identify(wav_uri)`, `enroll(name, wav_uri)`, with `speaker_id_global` returned.
   - Maintain alias table for human overrides.

4. **Testing**
   - Tests assume Deepgram as primary ASR.
   - Add mocked tests for Speaker Platform (identify & enroll).

5. **Setup & Ops**
   - `.env.example` must include: DEEPGRAM_API_KEY, PYANNOTE_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY.
   - Secrets doc updated accordingly.
   - Error playbook covers Deepgram, Precision-2, Speaker Platform, and Inngest retries.
   - Observability tracks events (`episode.new`, `episode.processed`, `speaker.identified`).

6. **API**
   - Expose `GET /episodes/{id}` → transcript JSON with speaker IDs.
   - Optionally `POST /episodes/{id}/reprocess` → triggers Inngest event.

---

## 📌 Notes

- Whisper is optional, not primary.  
- ECAPA and Fly.io are **not** part of the default stack.  
- Self-hosted diarization/speaker memory may be reintroduced later as v2.  

---
