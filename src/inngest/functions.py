"""
Inngest function definitions for Read The Game podcast pipeline.
These functions are orchestrated by Inngest for durable, retryable workflows.
"""

import os
import inngest
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from ..pipeline.rss_processor import RSSProcessor
from ..pipeline.audio_downloader import AudioDownloader
from ..pipeline.diarization import DiarizationService
from ..pipeline.transcription import TranscriptionService
from ..pipeline.speaker_id_service import SpeakerMemory, SpeakerPlatformClient
from ..pipeline.indexing import IndexingService
from ..db.supabase import SupabaseClient

logger = logging.getLogger(__name__)

client = inngest.Inngest(
    app_id="read-the-game",
    event_key=os.getenv("INNGEST_EVENT_KEY"),
)


@client.create_function(
    fn_id="process-new-episode",
    trigger=inngest.TriggerEvent(event="episode.new"),
    retries=3,
)
async def process_new_episode(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main orchestration function triggered by episode.new event.
    Coordinates the entire pipeline from RSS discovery to indexed transcript.
    """
    episode_id = event.get("data", {}).get("episode_id")
    audio_url = event.get("data", {}).get("audio_url")

    logger.info(f"Processing new episode: {episode_id}")

    # Step 1: Download audio
    audio_path = await step.run(
        "download-audio",
        lambda: AudioDownloader().download(audio_url, episode_id)
    )

    # Step 2: Diarization (speaker segmentation)
    diarization_result = await step.run(
        "diarize-audio",
        lambda: DiarizationService().diarize(audio_path)
    )

    # Step 3: Transcription (ASR)
    transcript = await step.run(
        "transcribe-audio",
        lambda: TranscriptionService().transcribe(audio_path, diarization_result)
    )

    # Step 4: Speaker Identification
    identified_transcript = await step.run(
        "identify-speakers",
        lambda: identify_speakers_task(audio_path, transcript, episode_id)
    )

    # Step 5: Index and Store
    indexed_result = await step.run(
        "index-transcript",
        lambda: IndexingService().index(episode_id, identified_transcript)
    )

    # Send completion event
    await step.send_event(
        "episode-processed",
        {
            "name": "episode.processed",
            "data": {
                "episode_id": episode_id,
                "transcript_id": indexed_result.get("transcript_id"),
                "duration": indexed_result.get("duration"),
                "speaker_count": indexed_result.get("speaker_count"),
            }
        }
    )

    return {
        "episode_id": episode_id,
        "status": "completed",
        "transcript_id": indexed_result.get("transcript_id"),
    }


@client.create_function(
    fn_id="diarize-episode",
    trigger=inngest.TriggerEvent(event="episode.downloaded"),
    retries=2,
)
async def diarize_episode(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diarization function using pyannote Precision-2.
    Identifies speaker turns and segments in the audio.
    """
    audio_path = event.get("data", {}).get("audio_path")
    episode_id = event.get("data", {}).get("episode_id")

    logger.info(f"Starting diarization for episode: {episode_id}")

    service = DiarizationService()
    diarization_result = await step.run(
        "run-diarization",
        lambda: service.diarize(audio_path)
    )

    # Send event for next step
    await step.send_event(
        "diarization-complete",
        {
            "name": "episode.diarized",
            "data": {
                "episode_id": episode_id,
                "audio_path": audio_path,
                "diarization": diarization_result,
                "speaker_count": len(diarization_result.get("speakers", [])),
            }
        }
    )

    return diarization_result


@client.create_function(
    fn_id="transcribe-episode",
    trigger=inngest.TriggerEvent(event="episode.diarized"),
    retries=3,
)
async def transcribe_episode(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcription function using Deepgram (primary) or Whisper (optional fallback).
    Generates timestamped text aligned with speaker segments.
    """
    audio_path = event.get("data", {}).get("audio_path")
    episode_id = event.get("data", {}).get("episode_id")
    diarization = event.get("data", {}).get("diarization", {})

    logger.info(f"Starting transcription for episode: {episode_id}")

    service = TranscriptionService()

    # Try Deepgram first
    transcript = await step.run(
        "transcribe-deepgram",
        lambda: service.transcribe_with_deepgram(audio_path, diarization)
    )

    # If Deepgram fails and Whisper is configured, use as fallback
    if not transcript and service.whisper_available():
        logger.warning("Deepgram failed, falling back to Whisper")
        transcript = await step.run(
            "transcribe-whisper",
            lambda: service.transcribe_with_whisper(audio_path, diarization)
        )

    # Send event for next step
    await step.send_event(
        "transcription-complete",
        {
            "name": "episode.transcribed",
            "data": {
                "episode_id": episode_id,
                "audio_path": audio_path,
                "transcript": transcript,
                "word_count": len(transcript.get("text", "").split()),
            }
        }
    )

    return transcript


@client.create_function(
    fn_id="identify-speakers",
    trigger=inngest.TriggerEvent(event="episode.transcribed"),
    retries=2,
)
async def identify_speakers(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Speaker identification using pyannote Speaker Platform.
    Matches speakers against known voiceprints and maintains cross-episode memory.
    """
    episode_id = event.get("data", {}).get("episode_id")
    audio_path = event.get("data", {}).get("audio_path")
    transcript = event.get("data", {}).get("transcript", {})

    logger.info(f"Starting speaker identification for episode: {episode_id}")

    identified_transcript = await step.run(
        "run-speaker-id",
        lambda: identify_speakers_task(audio_path, transcript, episode_id)
    )

    # Send event for next step
    await step.send_event(
        "speaker-id-complete",
        {
            "name": "speaker.identified",
            "data": {
                "episode_id": episode_id,
                "transcript": identified_transcript,
                "speakers": extract_speaker_list(identified_transcript),
            }
        }
    )

    return identified_transcript


def identify_speakers_task(audio_path: str, transcript: Dict, episode_id: str) -> Dict:
    """
    Task to identify speakers using pyannote Speaker Platform API.
    """
    client = SpeakerPlatformClient()
    memory = SpeakerMemory()

    # Extract speaker segments from transcript
    segments = transcript.get("segments", [])

    identified_segments = []
    for segment in segments:
        # Get speaker embedding from audio segment
        start_time = segment.get("start")
        end_time = segment.get("end")

        # Call Speaker Platform API to identify speaker
        speaker_id = client.identify(
            wav_uri=audio_path,
            start_ms=int(start_time * 1000),
            end_ms=int(end_time * 1000)
        )

        # Map to human-friendly name using memory/alias table
        speaker_name = memory.get_speaker_name(speaker_id)

        # Update segment with identified speaker
        segment["speaker_id_global"] = speaker_id
        segment["speaker_name"] = speaker_name
        identified_segments.append(segment)

    transcript["segments"] = identified_segments
    return transcript


@client.create_function(
    fn_id="index-transcript",
    trigger=inngest.TriggerEvent(event="speaker.identified"),
    retries=2,
)
async def index_transcript(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Index the final transcript with speaker IDs into Supabase with pgvector embeddings.
    """
    episode_id = event.get("data", {}).get("episode_id")
    transcript = event.get("data", {}).get("transcript", {})

    logger.info(f"Indexing transcript for episode: {episode_id}")

    service = IndexingService()
    result = await step.run(
        "index-to-supabase",
        lambda: service.index_transcript(episode_id, transcript)
    )

    # Send completion event
    await step.send_event(
        "indexing-complete",
        {
            "name": "episode.indexed",
            "data": {
                "episode_id": episode_id,
                "transcript_id": result.get("transcript_id"),
                "chunk_count": result.get("chunk_count"),
                "embedding_count": result.get("embedding_count"),
            }
        }
    )

    return result


@client.create_function(
    fn_id="poll-rss-feed",
    trigger=inngest.TriggerCron(cron="0 */6 * * *"),  # Every 6 hours
)
async def poll_rss_feed(step: inngest.Step) -> Dict[str, Any]:
    """
    Periodic RSS feed polling to discover new episodes.
    """
    logger.info("Polling RSS feed for new episodes")

    processor = RSSProcessor()
    new_episodes = await step.run(
        "check-rss",
        lambda: processor.check_for_new_episodes()
    )

    # Trigger episode.new event for each new episode
    for episode in new_episodes:
        await step.send_event(
            f"new-episode-{episode['guid']}",
            {
                "name": "episode.new",
                "data": {
                    "episode_id": episode["guid"],
                    "title": episode["title"],
                    "audio_url": episode["audio_url"],
                    "published_at": episode["published_at"],
                }
            }
        )

    return {
        "episodes_found": len(new_episodes),
        "timestamp": datetime.utcnow().isoformat(),
    }


@client.create_function(
    fn_id="reprocess-episode",
    trigger=inngest.TriggerEvent(event="episode.reprocess"),
)
async def reprocess_episode(step: inngest.Step, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manually triggered reprocessing of an episode.
    Useful for fixing errors or testing improvements.
    """
    episode_id = event.get("data", {}).get("episode_id")

    logger.info(f"Reprocessing episode: {episode_id}")

    # Fetch episode details from database
    db = SupabaseClient()
    episode = await step.run(
        "fetch-episode",
        lambda: db.get_episode(episode_id)
    )

    if not episode:
        raise ValueError(f"Episode {episode_id} not found")

    # Trigger new processing
    await step.send_event(
        "reprocess-trigger",
        {
            "name": "episode.new",
            "data": {
                "episode_id": episode_id,
                "audio_url": episode["audio_url"],
                "is_reprocess": True,
            }
        }
    )

    return {
        "episode_id": episode_id,
        "status": "reprocessing_triggered",
    }


def extract_speaker_list(transcript: Dict) -> list:
    """Extract unique speaker names from transcript."""
    speakers = set()
    for segment in transcript.get("segments", []):
        if speaker_name := segment.get("speaker_name"):
            speakers.add(speaker_name)
    return list(speakers)