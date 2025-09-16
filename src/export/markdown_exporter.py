"""
Markdown exporter for Read The Game podcast transcripts.
Converts JSON transcript artifacts to structured Markdown files.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MarkdownExporter:
    """Converts episode transcript JSON to formatted Markdown."""

    def __init__(self, artifacts_dir: str = "artifacts"):
        """
        Initialize the Markdown exporter.

        Args:
            artifacts_dir: Base directory for storing artifacts
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def export_episode(self, transcript_json: Dict[str, Any]) -> str:
        """
        Convert a transcript JSON to Markdown format.

        Args:
            transcript_json: Episode transcript data

        Returns:
            Formatted Markdown string
        """
        # Extract metadata
        episode_id = transcript_json.get("episode_id", "unknown")
        title = transcript_json.get("title", "Untitled Episode")
        date = transcript_json.get("date", datetime.now().strftime("%Y-%m-%d"))
        audio_url = transcript_json.get("audio_url", "")
        duration = transcript_json.get("duration", 0)
        summary = transcript_json.get("summary", "")

        # Extract speakers
        speakers = self._extract_speakers(transcript_json)

        # Build front matter
        front_matter = self._build_front_matter(
            episode_id=episode_id,
            title=title,
            date=date,
            audio_url=audio_url,
            duration=duration,
            summary=summary,
            speakers=speakers
        )

        # Build body content
        body = self._build_body(
            title=title,
            audio_url=audio_url,
            segments=transcript_json.get("segments", [])
        )

        return f"{front_matter}\n{body}"

    def _extract_speakers(self, transcript_json: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract unique speakers from transcript segments."""
        speakers_dict = {}

        for segment in transcript_json.get("segments", []):
            speaker_id = segment.get("speaker_id_global", segment.get("speaker", "unknown"))
            speaker_name = segment.get("speaker_name", speaker_id)

            if speaker_id not in speakers_dict:
                speakers_dict[speaker_id] = {
                    "id": speaker_id,
                    "display_name": speaker_name
                }

        # Ensure Alex Hormozi is listed first if present
        speakers_list = list(speakers_dict.values())
        speakers_list.sort(key=lambda s: (s["id"] != "alex_hormozi", s["id"]))

        return speakers_list

    def _build_front_matter(
        self,
        episode_id: str,
        title: str,
        date: str,
        audio_url: str,
        duration: int,
        summary: str,
        speakers: List[Dict[str, str]]
    ) -> str:
        """Build YAML front matter for the Markdown file."""
        lines = ["---"]
        lines.append(f'episode_id: "{episode_id}"')
        lines.append(f'title: "{title}"')
        lines.append(f'date: "{date}"')

        # Primary guest (usually Alex)
        if speakers:
            primary_speaker = next(
                (s for s in speakers if "alex" in s["id"].lower()),
                speakers[0] if speakers else {"display_name": "Unknown"}
            )
            lines.append(f'guest: "{primary_speaker["display_name"]}"')

        lines.append(f'audio_url: "{audio_url}"')

        if summary:
            lines.append("summary: |")
            for line in summary.split("\n"):
                lines.append(f"  {line}")

        lines.append(f"duration: {duration}   # in seconds")

        if speakers:
            lines.append("speakers:")
            for speaker in speakers:
                lines.append(f'  - id: "{speaker["id"]}"')
                lines.append(f'    display_name: "{speaker["display_name"]}"')

        lines.append("---")

        return "\n".join(lines)

    def _build_body(
        self,
        title: str,
        audio_url: str,
        segments: List[Dict[str, Any]]
    ) -> str:
        """Build the body content of the Markdown file."""
        lines = []

        # Title
        episode_num = self._extract_episode_number(title)
        if episode_num:
            lines.append(f"# Episode {episode_num} – {title}")
        else:
            lines.append(f"# {title}")

        lines.append("")

        # Audio player
        if audio_url:
            lines.append("Listen here:  ")
            lines.append(f'<audio controls src="{audio_url}"></audio>')
            lines.append("")
            lines.append("---")
            lines.append("")

        # Transcript
        lines.append("## Transcript")
        lines.append("")

        # Format segments
        for segment in segments:
            formatted_segment = self._format_segment(segment)
            if formatted_segment:
                lines.append(formatted_segment)
                lines.append("")

        return "\n".join(lines)

    def _extract_episode_number(self, title: str) -> Optional[str]:
        """Extract episode number from title if present."""
        import re

        patterns = [
            r"Episode\s+(\d+)",
            r"Ep\s+(\d+)",
            r"#(\d+)",
            r"(\d+)\s*[-–]\s*",
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _format_segment(self, segment: Dict[str, Any]) -> str:
        """Format a single transcript segment."""
        speaker_name = segment.get("speaker_name", segment.get("speaker", "Unknown"))
        text = segment.get("text", "")
        start_time = segment.get("start", 0)

        if not text.strip():
            return ""

        # Format timestamp as [MM:SS]
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"

        return f"**{speaker_name} {timestamp}:** {text}"

    def save_episode(
        self,
        episode_id: str,
        transcript_json: Dict[str, Any],
        markdown_content: Optional[str] = None
    ) -> tuple[Path, Path]:
        """
        Save both JSON and Markdown artifacts for an episode.

        Args:
            episode_id: Episode identifier
            transcript_json: Episode transcript data
            markdown_content: Pre-generated Markdown (optional)

        Returns:
            Tuple of (json_path, markdown_path)
        """
        # Create episode directory
        episode_dir = self.artifacts_dir / "episodes" / episode_id
        episode_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = episode_dir / "transcript.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(transcript_json, f, indent=2, ensure_ascii=False)

        # Generate and save Markdown
        if markdown_content is None:
            markdown_content = self.export_episode(transcript_json)

        markdown_path = episode_dir / "transcript.md"
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"Saved artifacts for episode {episode_id}:")
        logger.info(f"  JSON: {json_path}")
        logger.info(f"  Markdown: {markdown_path}")

        return json_path, markdown_path


def export_markdown_from_json(json_path: str, output_path: Optional[str] = None) -> str:
    """
    Convenience function to convert a JSON file to Markdown.

    Args:
        json_path: Path to transcript JSON file
        output_path: Optional output path for Markdown file

    Returns:
        Markdown content
    """
    with open(json_path, "r", encoding="utf-8") as f:
        transcript_json = json.load(f)

    exporter = MarkdownExporter()
    markdown = exporter.export_episode(transcript_json)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        logger.info(f"Exported Markdown to {output_path}")

    return markdown