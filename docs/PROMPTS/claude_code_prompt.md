
# Prompt for Claude Code — Read The Game Implementation

```
@claude

You are my repo assistant. Implement the Read The Game project step-by-step and report progress at every step.

## 📌 Context (read first)
- Architecture + scope are defined in these files (use them as the source of truth):
  - CLAUDE.md
  - docs/PRD/read_the_game_PRD_v4_1.md
  - docs/OPS/inngest_function_map.md
  - docs/SCHEMA/supabase.sql
  - docs/OPS/error_playbook_readthegame.md
  - docs/OPS/observability_readthegame.yaml
  - docs/OPS/secrets_management_readthegame.md
  - docs/API/openapi_readthegame.yaml
- Current stack: **Inngest (orchestration)**, **Deepgram (ASR primary)**, **pyannote Precision-2 (diarization)**, **pyannote Speaker Platform (speaker memory)**, **Supabase (storage/pgvector)**, **Vercel (frontend)**.
- No Fly.io or ECAPA by default. Whisper is optional.

## 🔁 Workstyle & Reporting
- Work in small, auditable steps.
- For each step, open **one PR** named `step-N-<short-title>`.
- In each PR description, include:
  - **Goal** (what and why)
  - **Summary of changes**
  - **Files touched**
  - **How to run/test locally**
  - **Backout plan**
- After opening each PR, **post a comment in this thread** with:
  - PR name + link
  - 3–5 line summary
  - Any questions/blockers
- Do not squash many unrelated changes into one PR.

## ✅ Acceptance criteria (global)
- Keep Deepgram primary (Whisper optional).
- Use pyannote Precision-2 and Speaker Platform (identify/enroll) APIs.
- Keep docs in sync only when needed, but do not rewrite PRD.
- Make CI (`.github/workflows/ci.yml`) pass: ruff, black --check, pytest -q.
- Preserve existing tests; extend with new mocks as needed.
- Add clear TODOs where a real key/URL is required.

## 🛠️ Planned steps (open PRs in order)

### PR 1 — Orchestrator app with Inngest (TypeScript)
**Goal:** Stand up a minimal Node/TS Inngest app that registers functions and exposes `/api/inngest` locally.
- Create folder `apps/orchestrator/` (Next.js route or Express — your call; Next.js recommended for Vercel).
- Dependencies: `@inngest/inngest`, `@inngest/next` or `express` + `@inngest/express`, `zod`.
- Register placeholder functions for:
  - `fetch_audio`, `diarize_episode`, `transcribe_episode`, `identify_speakers`, `index_episode`
- Wire an `episode.new` trigger + a test event sender in README of this app.
- Add a short `apps/orchestrator/README.md` with local dev instructions:
  ```
  npx inngest-cli@latest dev
  ```
**Acceptance:** Inngest Dev Server shows the functions; sending a test `episode.new` hits a placeholder function.

### PR 2 — Deepgram integration (ASR primary)
**Goal:** Real ASR call path.
- Add Deepgram client to orchestrator (`deepgram-sdk` or REST), env var `DEEPGRAM_API_KEY`.
- Implement `transcribe_episode` to call Deepgram (prerecorded by URL).
- Add a Jest test with a mocked response (no real API call).
- Update docs if needed: mention Deepgram in `apps/orchestrator/README.md`.
**Acceptance:** Unit test passes; function returns transcript shape `{ start, end, speaker, text }`.

### PR 3 — Precision-2 diarization integration
**Goal:** Real diarization call path.
- Implement `diarize_episode` via pyannote Precision-2 API (use REST if available).
- Define a small response adapter to normalize into `{ start, end, speaker }` per segment.
- Add a mocked unit test for the API call.
**Acceptance:** Unit test passes; diarization function returns normalized segments.

### PR 4 — Speaker Platform (speaker memory)
**Goal:** Cross-episode speaker identification.
- Option A (fast path): Implement a Node client to pyannote Speaker Platform (`identify`, `enroll`) in orchestrator, mirroring what exists in `src/pipeline/speaker_id_service.py`.
- Option B (bridge): If you prefer not to duplicate logic, create a tiny FastAPI service exposing `/identify` and `/enroll` that wraps `src/pipeline/speaker_id_service.py`, and call that from orchestrator. Document choice.
- Add mocked tests for identify (match) and identify (unknown→enroll).
**Acceptance:** Unit tests pass; `identify_speakers` returns mapping `{ "A": "alex_hormozi", "B": "guest" }`.

### PR 5 — Supabase writes (episodes, segments, artifacts)
**Goal:** Persist pipeline outputs.
- Use `@supabase/supabase-js` in orchestrator to upsert:
  - `episodes` (id, guid, title, publish_date, audio_uri)
  - `segments` (episode_id, start_seconds, end_seconds, speaker_global_id, text)
- If using JSON artifacts, write them to Supabase Storage or reference an external bucket URI in `artifacts`.
- Add env: `SUPABASE_URL`, `SUPABASE_ANON_KEY` (stored securely).
- Add unit/integration test that stubs Supabase client calls.
**Acceptance:** Test passes; function returns `{ episode_id, status: "indexed" }`.

### PR 6 — Wire the event graph & idempotency
**Goal:** Connect steps and add reliability.
- Implement event chaining: `episode.new -> fetch_audio -> diarize_episode -> transcribe_episode -> identify_speakers -> index_episode -> episode.processed`.
- Add idempotency keys (e.g., `episode_id:step`) to skip duplicates.
- Add retries/backoff via Inngest where applicable.
- Update `docs/OPS/inngest_function_map.md` only if naming diverged.
**Acceptance:** A test run in Dev Server shows the full chain executing with mocked calls.

### PR 7 — Observability & CI polish
**Goal:** Instrumentation + rock-solid CI.
- Emit counters aligned with `docs/OPS/observability_readthegame.yaml`: `episode.new`, `episode.processed`, `speaker.identified`, `speaker.unknown`, `retries`.
- Ensure `pytest -q` passes, plus add any Jest tests to the Node app.
- Keep `.github/workflows/ci.yml` passing (python + node steps if needed).
**Acceptance:** CI green; basic metrics log statements present.

## 🔐 Environment & Security
- Do not commit real keys.
- For every new env var, update:
  - `.env.example`
  - `docs/OPS/secrets_management_readthegame.md`
  - `apps/orchestrator/README.md` (if created)

## 🧪 Testing
- Python tests continue to run: `tests/test_speaker_memory.py`, `tests/test_transcription.py`.
- Node tests use Jest + nock/msw or simple custom mocks.
- No live network calls in CI.

## 🚫 Non-Goals
- No Fly.io, no ECAPA.
- No local heavy diarization unless explicitly requested.

## 📣 Deliverable for each step
- Open the PR, then **comment back here** with:
  - PR link and a 3–5 line summary,
  - how to run it locally,
  - any open questions or tradeoffs.

Begin with **PR 1 — Orchestrator app with Inngest**.
```
