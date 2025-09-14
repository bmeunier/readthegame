# src/inngest/functions.py
"""
Inngest Function Stubs wired to real service call sites.
Replace TODOs with actual implementations (Deepgram, pyannote, Supabase).
"""
from __future__ import annotations

import os
from typing import Dict, Any, List

# Deepgram SDK placeholder (import if installed)
try:
    from deepgram import Deepgram
except Exception:  # pragma: no cover
    Deepgram = None  # type: ignore

# HTTP for pyannote Precision-2 (if using REST); otherwise use their SDK if/when available
import requests

# Supabase (python client)
try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None
    Client = None  # type: ignore

from src.pipeline.speaker_id_service import SpeakerMemory, SpeakerPlatformClient

# ----------------
# Helpers / Config
# ----------------

def _supabase() -> Any:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not (url and key):
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    if not create_client:
        raise RuntimeError("supabase client not installed")
    return create_client(url, key)

def _deepgram() -> Any:
    if not Deepgram:
        raise RuntimeError("deepgram-sdk not installed")
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise RuntimeError("Missing DEEPGRAM_API_KEY")
    return Deepgram(key)

def _pyannote_headers() -> Dict[str, str]:
    key = os.getenv("PYANNOTE_API_KEY")
    if not key:
        raise RuntimeError("Missing PYANNOTE_API_KEY")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# ----------------
# Pipeline steps
# ----------------

def fetch_audio(event: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger: episode.new
    Action: download audio and return path/URI (stub: assume remote URI is valid).
    """
    episode_id = event.get("episode_id")
    audio_url = event.get("audio_url")
    # TODO: actually download to storage (Supabase Storage or S3) and return a URI
    audio_uri = audio_url  # For now, pass-through
    return {"episode_id": episode_id, "audio_uri": audio_uri}

def diarize_episode(event: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger: audio.fetched → call pyannote Precision-2
    Expected response: list of segments [{start,end,speaker_local}].
    """
    episode_id = event["episode_id"]
    audio_uri = event["audio_uri"]
    # TODO: Replace with real Precision-2 API call
    # Example shape (dummy)
    segments: List[Dict[str, Any]] = [
        {"start": 0.0, "end": 5.0, "speaker": "A"},
        {"start": 5.0, "end": 10.0, "speaker": "B"},
    ]
    return {"episode_id": episode_id, "audio_uri": audio_uri, "segments": segments}

def transcribe_episode(event: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger: episode.diarized → call Deepgram primary (Whisper optional).
    Returns a transcript aligned to diarized segments if possible.
    """
    episode_id = event["episode_id"]
    audio_uri = event["audio_uri"]

    # Deepgram example call (pseudo; adapt to actual SDK usage)
    dg = _deepgram()
    # NOTE: Use remote URL or streamed bytes
    # response = dg.transcription.prerecorded({"url": audio_uri}, {"smart_format": True})
    # For now, dummy transcript aligned roughly with diarization:
    transcript = [
        {"start": 0.0, "end": 5.0, "speaker": "A", "text": "Hello world"},
        {"start": 5.0, "end": 10.0, "speaker": "B", "text": "This is a test"},
    ]
    return {"episode_id": episode_id, "audio_uri": audio_uri, "transcript": transcript}

def identify_speakers(event: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger: episode.transcribed → map local speakers to global IDs via Speaker Platform.
    """
    episode_id = event["episode_id"]
    transcript = event["transcript"]

    # For each local speaker, create a snippet URI (TODO) then call identify/enroll
    client = SpeakerPlatformClient()
    memory = SpeakerMemory(client, aliases={})
    # Dummy mapping
    local_to_global = {"A": "alex_hormozi", "B": "guest1"}
    # TODO: Implement per-speaker snippet extraction and call:
    # res = memory.identify_or_enroll(local_label, wav_uri)
    return {"episode_id": episode_id, "speaker_map": local_to_global, "transcript": transcript}

def index_episode(event: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger: speaker.identified → persist to Supabase (tables + storage JSON).
    """
    episode_id = event["episode_id"]
    speaker_map = event["speaker_map"]
    transcript = event["transcript"]

    # Persist JSON artifact and records
    sb = _supabase()
    # Example schema: episodes (id,title), segments (episode_id,start,end,speaker_id_global,text)
    # TODO: Upsert into episodes
    # sb.table("episodes").upsert({"id": episode_id, "title": "Unknown"}).execute()
    # TODO: Upsert segments
    # for seg in transcript:
    #     gid = speaker_map.get(seg["speaker"], seg["speaker"])
    #     sb.table("segments").insert({ ... }).execute()

    return {"episode_id": episode_id, "status": "indexed"}