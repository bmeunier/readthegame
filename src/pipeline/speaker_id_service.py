"""
speaker_id_service.py

Handles speaker memory using pyannote Speaker Platform.
Provides identify and enroll operations, with optional alias overrides.
"""

import os
import requests
from typing import Dict, Optional


class SpeakerPlatformClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.pyannote.ai/speaker-platform"):
        self.api_key = api_key or os.getenv("PYANNOTE_API_KEY")
        if not self.api_key:
            raise ValueError("Missing PYANNOTE_API_KEY")
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def identify(self, wav_uri: str) -> Dict:
        """
        Identify a speaker from an audio snippet.
        Returns: {speaker_id_global, score, decision}
        """
        url = f"{self.base_url}/identify"
        payload = {"wav_uri": wav_uri}
        resp = requests.post(url, headers=self.headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def enroll(self, name: str, wav_uri: str) -> str:
        """
        Enroll a new speaker voiceprint.
        Returns: speaker_id_global
        """
        url = f"{self.base_url}/enroll"
        payload = {"name": name, "wav_uri": wav_uri}
        resp = requests.post(url, headers=self.headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("speaker_id_global")


class SpeakerMemory:
    def __init__(self, client: SpeakerPlatformClient, aliases: Optional[Dict[str, str]] = None):
        """
        aliases: dict mapping variants ("alex", "Alex Hormozi") → canonical speaker_id_global ("alex_hormozi")
        """
        self.client = client
        self.aliases = aliases or {}

    def identify_or_enroll(self, local_label: str, wav_uri: str) -> Dict:
        """
        Identify a speaker, or enroll if unknown.
        Applies alias overrides if available.
        """
        result = self.client.identify(wav_uri)

        # Apply alias override if configured
        global_id = result.get("speaker_id_global")
        if global_id in self.aliases:
            result["speaker_id_global"] = self.aliases[global_id]

        # Example: handle unknown → enroll flow (pseudo-logic, depends on API contract)
        if result.get("decision") == "unknown":
            enrolled_id = self.client.enroll(local_label, wav_uri)
            result["speaker_id_global"] = enrolled_id
            result["decision"] = "enrolled"

        return result