# src/pipeline/speaker_id_service.py
"""
Speaker memory client using pyannote Speaker Platform.
- Adds timeouts, retries with backoff, and clear exceptions.
- Provides identify() and enroll() primitives.
- SpeakerMemory wraps the client and applies alias overrides + 'unknown→enroll' policy.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Any

import requests


# ---------- Exceptions ----------
class SpeakerPlatformError(Exception):
    pass


class SpeakerPlatformAuthError(SpeakerPlatformError):
    pass


class SpeakerPlatformRateLimit(SpeakerPlatformError):
    pass


class SpeakerPlatformUnavailable(SpeakerPlatformError):
    pass


# ---------- HTTP Client ----------
@dataclass
class HTTPConfig:
    base_url: str = "https://api.pyannote.ai/speaker-platform"
    timeout: int = 60
    max_retries: int = 3
    backoff_seconds: float = 1.5


class SpeakerPlatformClient:
    def __init__(self, api_key: Optional[str] = None, http: Optional[HTTPConfig] = None):
        self.api_key = api_key or os.getenv("PYANNOTE_API_KEY")
        if not self.api_key:
            raise ValueError("Missing PYANNOTE_API_KEY")
        self.http = http or HTTPConfig()
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self.api_key}",
                                      "Content-Type": "application/json"})

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.http.base_url}{path}"
        last_err: Optional[Exception] = None
        for attempt in range(1, self.http.max_retries + 1):
            try:
                resp = self._session.post(url, json=payload, timeout=self.http.timeout)
                if resp.status_code == 401:
                    raise SpeakerPlatformAuthError("Invalid or missing PYANNOTE_API_KEY")
                if resp.status_code == 429:
                    raise SpeakerPlatformRateLimit("Rate limited by Speaker Platform")
                if 500 <= resp.status_code < 600:
                    raise SpeakerPlatformUnavailable(f"Upstream error {resp.status_code}")
                resp.raise_for_status()
                return resp.json()
            except (SpeakerPlatformError, requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                if attempt == self.http.max_retries:
                    break
                # simple exponential backoff
                time.sleep(self.http.backoff_seconds * attempt)
        # If we reach here, bubble the last error
        if isinstance(last_err, SpeakerPlatformError):
            raise last_err
        raise SpeakerPlatformError(f"Request failed after retries: {last_err}")

    # ----- Public API -----
    def identify(self, wav_uri: str) -> Dict[str, Any]:
        """Identify a speaker from an audio snippet.
        Returns: {speaker_id_global, score, decision} where decision ∈ {"match","unknown"}
        """
        return self._post("/identify", {"wav_uri": wav_uri})

    def enroll(self, name: str, wav_uri: str) -> str:
        """Enroll a new speaker voiceprint and return speaker_id_global."""
        data = self._post("/enroll", {"name": name, "wav_uri": wav_uri})
        return data.get("speaker_id_global")


# ---------- Memory wrapper ----------
class SpeakerMemory:
    def __init__(self, client: SpeakerPlatformClient, aliases: Optional[Dict[str, str]] = None):
        self.client = client
        self.aliases = aliases or {}

    def identify_or_enroll(self, local_label: str, wav_uri: str, allow_enroll: bool = True) -> Dict[str, Any]:
        res = self.client.identify(wav_uri)
        gid = res.get("speaker_id_global")

        # Apply alias if we already mapped this gid
        if gid and gid in self.aliases:
            res["speaker_id_global"] = self.aliases[gid]

        if res.get("decision") == "unknown" and allow_enroll:
            enrolled_id = self.client.enroll(local_label, wav_uri)
            res.update({"speaker_id_global": enrolled_id, "decision": "enrolled"})
        return res