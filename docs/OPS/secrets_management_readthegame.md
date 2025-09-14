# Secrets Management — Read The Game

This document describes all required secrets and how they are stored.

---

## Required Secrets

### 🔑 Deepgram
- **Key:** `DEEPGRAM_API_KEY`
- **Purpose:** Primary ASR (speech-to-text)
- **Notes:** Scoped to audio transcription

### 🔑 pyannote
- **Key:** `PYANNOTE_API_KEY`
- **Purpose:** Access to Precision-2 (diarization) and Speaker Platform (speaker memory)
- **Notes:** Must be kept private; high-rate usage may require quota upgrade

### 🔑 Supabase
- **Keys:**
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
- **Purpose:** Database (Postgres + pgvector) and storage for JSON artifacts
- **Notes:** `anon` key is for client apps; service role key may be needed for server-side batch jobs

---

## Storage & Access

- Secrets are stored in:
  - Local `.env` file for dev
  - Vercel environment variables for frontend
  - Inngest environment variables for orchestration
- Never commit `.env` files to Git

---

## Rotation Policy

- Rotate all API keys every 90 days or on suspected compromise
- Document rotation in commit notes
- Validate rotated keys by re-running a test ingestion

---

## Handling Failures

- If key is missing or invalid:
  - Deepgram → returns 401  
  - pyannote → returns 401  
  - Supabase → connection error  

Resolution: verify environment variables are set and valid.