from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.db import SessionLocal
from src.models.db_models import EpisodeRow, TranscriptRow, UtteranceRow

app = FastAPI(title="Read The Game")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

# ---- Response models ----
class EpisodeOut(BaseModel):
    guid: str
    title: str
    publish_date: str | None = None
    audio_url: str
    duration_sec: int | None = None
    summary: str | None = None

class UtteranceOut(BaseModel):
    start: float
    end: float
    text: str
    speaker: str
    confidence: float | None = None

class TranscriptOut(BaseModel):
    guid: str
    utterances: list[UtteranceOut]

# ---- Endpoints ----
@app.get("/episodes/{guid}", response_model=EpisodeOut)
def get_episode(guid: str, db: Session = Depends(get_db)):
    row = db.get(EpisodeRow, guid)
    if not row:
        raise HTTPException(404, "Not found")
    return EpisodeOut(
        guid=str(row.guid),
        title=row.title,
        publish_date=row.publish_date.isoformat() if row.publish_date else None,
        audio_url=row.audio_url,
        duration_sec=row.duration_sec,
        summary=row.summary,
    )

@app.get("/episodes/{guid}/transcript", response_model=TranscriptOut)
def get_transcript(guid: str, db: Session = Depends(get_db)):
    tr = db.execute(select(TranscriptRow).where(TranscriptRow.episode_guid == guid)).scalars().first()
    if not tr:
        raise HTTPException(404, "Not found")
    utts = db.execute(
        select(UtteranceRow)
        .where(UtteranceRow.transcript_id == tr.id)
        .order_by(UtteranceRow.start_sec)
    ).scalars().all()
    return TranscriptOut(
        guid=guid,
        utterances=[
            UtteranceOut(
                start=float(u.start_sec),
                end=float(u.end_sec),
                text=u.text,
                speaker=u.speaker_label,
                confidence=float(u.confidence) if u.confidence is not None else None,
            ) for u in utts
        ],
    )