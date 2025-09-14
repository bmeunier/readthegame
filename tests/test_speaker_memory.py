# tests/test_speaker_memory.py

import pytest
from src.pipeline.speaker_id_service import SpeakerMemory, SpeakerPlatformClient


class DummyClient:
    """Mocked pyannote Speaker Platform client."""

    def identify(self, wav_uri: str):
        if "alex" in wav_uri:
            return {"speaker_id_global": "alex_hormozi", "score": 0.95, "decision": "match"}
        return {"speaker_id_global": None, "score": 0.0, "decision": "unknown"}

    def enroll(self, name: str, wav_uri: str):
        return f"{name.lower()}_enrolled"


def test_identify_known_speaker():
    client = DummyClient()
    memory = SpeakerMemory(client)
    res = memory.identify_or_enroll("Alex", "file://alex_clip.wav")
    assert res["speaker_id_global"] == "alex_hormozi"
    assert res["decision"] == "match"


def test_enroll_unknown_speaker():
    client = DummyClient()
    memory = SpeakerMemory(client)
    res = memory.identify_or_enroll("Guest1", "file://guest_clip.wav")
    assert res["speaker_id_global"] == "guest1_enrolled"
    assert res["decision"] == "enrolled"


def test_alias_override():
    client = DummyClient()
    aliases = {"alex_hormozi": "alex"}
    memory = SpeakerMemory(client, aliases=aliases)
    res = memory.identify_or_enroll("Alex", "file://alex_clip.wav")
    assert res["speaker_id_global"] == "alex"  # alias applied