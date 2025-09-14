# Error Playbook — Read The Game

This playbook documents common errors in the pipeline and how to handle them.

---

## Deepgram (ASR)

**Symptoms:**
- 4xx: Invalid API key or unsupported audio format
- 429: Rate limiting
- 5xx: Service outage

**Actions:**
- Verify `DEEPGRAM_API_KEY`
- Backoff + retry with exponential delay
- Switch to Whisper fallback if persistent

---

## pyannote Precision-2 (Diarization API)

**Symptoms:**
- 401: Missing/invalid `PYANNOTE_API_KEY`
- 429: Too many requests
- 5xx: Service unavailable

**Actions:**
- Verify API key
- Backoff + retry
- Cache audio segments and reprocess later

---

## pyannote Speaker Platform

**Symptoms:**
- Identify returns `"decision": "unknown"`
- Enrollment fails with 4xx (bad audio)
- 5xx errors

**Actions:**
- Retry with backoff
- Allow human override / alias mapping
- Log “unknown” and proceed with temporary ID

---

## Inngest (Workflow Orchestration)

**Symptoms:**
- Function step stuck or failed
- Repeated retries not resolving

**Actions:**
- Use Inngest dashboard to inspect run
- Replay failed step
- Add idempotency guards if duplicate events suspected

---

## Supabase (Storage + pgvector)

**Symptoms:**
- Insert/update errors
- Connection timeout
- Index query fails

**Actions:**
- Retry with backoff
- Validate schema migrations
- Fail gracefully and reprocess episode later

---

## General Guidance

- Always log errors with episode ID, step, and payload reference
- Prefer retries with backoff over silent fails
- Where possible, continue downstream with partial data and mark artifact as “incomplete”