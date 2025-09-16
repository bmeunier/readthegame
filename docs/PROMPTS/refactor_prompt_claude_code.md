# Refactor Prompt for Claude Code — ReadTheGame

## 🎯 Objective
Refactor the `readthegame` repo to **remove all frontend aspects** and make the pipeline focus only on:  
1. **Pipeline ingestion and processing** (Inngest orchestrated).  
2. **JSON artifact export** (canonical per-episode data).  
3. **Markdown export** generated from JSON artifacts.  

The frontend (Next.js, Vercel, Astro, etc.) is out of scope and should be removed. The repo should be focused, backend-only, and future-proof.

---

## 📜 Markdown Schema Contract

Each episode transcript should be exported as a **Markdown file** with the following structure:

### 1. YAML Front-Matter
```yaml
---
episode_id: "ep-0042"
title: "Pricing Mistakes and Lessons"
date: "2025-09-10"
guest: "Alex Hormozi"
audio_url: "https://cdn.readthegame.com/audio/ep42.mp3"
summary: |
  In this episode Alex breaks down why most businesses underprice
  and how to avoid the most common traps.
duration: 2145   # in seconds
speakers:
  - id: "alex_hormozi"
    display_name: "Alex Hormozi"
  - id: "guest_1"
    display_name: "Guest"
---
```

### 2. Body Content
```markdown
# Episode 42 – Pricing Mistakes and Lessons

Listen here:  
<audio controls src="https://cdn.readthegame.com/audio/ep42.mp3"></audio>

---

## Transcript

**Alex Hormozi [00:00:05]:** Today I want to talk about…  

**Guest [00:01:12]:** Yeah, I made that mistake too…  

**Alex Hormozi [00:02:34]:** Exactly, and here’s why…  
```

---

## ⚙️ Inngest Integration

Add a final step in the Inngest pipeline that:  
- Listens for `transcript.generated` events.  
- Loads the per-episode `transcript.json`.  
- Converts it to Markdown using the schema above.  
- Saves both `.json` and `.md` into `/artifacts/episodes/[episode_id]/`.  

Example (Python pseudo-code):

```python
@inngest.function("Export Markdown", on_event="transcript.generated")
def export_markdown(event: InngestEvent):
    episode_id = event.data["episode_id"]
    transcript_json = load_json(episode_id)
    markdown = generate_markdown(transcript_json)
    save_to_storage(f"episodes/{episode_id}/transcript.md", markdown)
```

---

## 🔨 Required Changes

1. **Remove frontend code**  
   - Delete or archive `frontend_stub` and any other frontend/Vercel code.  
   - Update docs/PRD to remove "Phase 6: Frontend Rendering". Replace with "Phase 6: Markdown Export".  

2. **Add Markdown Export Module**  
   - New module: `export_markdown.py` (or similar).  
   - Implements JSON → Markdown conversion.  
   - Tested with sample `transcript.json`.  

3. **Update Inngest Workflow**  
   - Add Markdown export step after JSON is generated.  
   - Ensure artifacts are saved under `/artifacts/episodes/[episode_id]/`.  

4. **Docs & PRD**  
   - Update PRD to reflect Markdown-first strategy.  
   - Clearly define that frontend rendering is out-of-repo and not in scope here.  

---

## ✅ Deliverables

- Clean repo with no frontend code.  
- JSON + Markdown artifacts produced per episode.  
- Inngest workflow updated to include Markdown export.  
- Updated documentation and PRD to match.  

---
