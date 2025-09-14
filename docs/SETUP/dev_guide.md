# Developer Onboarding — Read The Game

Welcome! This guide gets you from zero → local dev in minutes.

---

## 1) Prereqs

- Python 3.11+
- Node 18+
- Make (optional, for shortcuts)
- A Supabase project
- API keys for:
  - Deepgram → `DEEPGRAM_API_KEY`
  - pyannote → `PYANNOTE_API_KEY`
  - Supabase → `SUPABASE_URL`, `SUPABASE_ANON_KEY`

---

## 2) Clone & Install

```bash
git clone <your-fork-url> readthegame
cd readthegame

# Python deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (Optional) ML local deps for experiments
# pip install -r requirements-ml-optional.txt
```

---

## 3) Environment

Copy and edit env files:

```bash
cp .env.example .env
# set DEEPGRAM_API_KEY, PYANNOTE_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY
```

---

## 4) Database (Supabase)

Run the SQL schema in Supabase (Web Console → SQL Editor):

- File: `docs/SCHEMA/supabase.sql`
- This creates tables: `episodes`, `speakers`, `segments`, `artifacts`

Optional: seed a speaker
```sql
insert into public.speakers (id, display_name, aliases)
values ('alex_hormozi', 'Alex Hormozi', '{Alex,Alex H.}')
on conflict (id) do nothing;
```

---

## 5) Services (local)

### API (FastAPI or your chosen server)
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

*(If `src.api` isn't set yet, skip this step for now.)*

### Inngest Dev Server
Run this from your web app project (or once your server exposes `/api/inngest`):
```bash
npx inngest-cli@latest dev
```
This gives you local parity for event triggers, retries, and replays.

---

## 6) Tests

```bash
pytest -q
```

- `tests/test_speaker_memory.py` → mocks pyannote Speaker Platform identify & enroll
- `tests/test_transcription.py` → mocks Deepgram call

---

## 7) Frontend (Next.js stub)

A minimal frontend is provided under `frontend_stub/`.

```bash
cd frontend_stub
cp .env.example .env.local
npm install
npm run dev
# open http://localhost:3000/episodes/<uuid-or-guid>
```

---

## 8) Development Flow

1. Add an RSS item or an episode manually and emit `episode.new`
2. Inngest runs: fetch → diarize → transcribe → identify → index
3. Data lands in Supabase (`episodes`, `segments`), artifacts saved if configured
4. Frontend reads from Supabase and renders `/episodes/[id]`

---

## 9) Troubleshooting

- **401 / 403** → check API keys in `.env`
- **429** (rate limiting) → retry with backoff (already baked into our clients)
- **Speaker unknown** → allow enroll or set a manual alias
- **Supabase writes failing** → check table names and RLS settings

---

## 10) Useful Files

- PRD → `docs/PRD/read_the_game_PRD_v4_1.md`
- Inngest function map → `docs/OPS/inngest_function_map.md`
- Error playbook → `docs/OPS/error_playbook_readthegame.md`
- Observability → `docs/OPS/observability_readthegame.yaml`
- API spec → `docs/API/openapi_readthegame.yaml`

---

## 11) CI

We run lint + tests on PRs:
- `.github/workflows/ci.yml` runs `ruff`, `black --check`, and `pytest -q`

---

Happy building! 🚀