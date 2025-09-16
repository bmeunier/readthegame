"""
Tests for the Markdown exporter module.
"""

import json
import pytest
from pathlib import Path
from src.export.markdown_exporter import MarkdownExporter, export_markdown_from_json


@pytest.fixture
def sample_transcript():
    """Sample transcript JSON for testing."""
    return {
        "episode_id": "ep-0042",
        "title": "Pricing Mistakes and Lessons",
        "date": "2025-09-10",
        "audio_url": "https://cdn.example.com/audio/ep42.mp3",
        "duration": 2145,
        "summary": "In this episode Alex breaks down why most businesses underprice\nand how to avoid the most common traps.",
        "segments": [
            {
                "start": 5.0,
                "end": 15.0,
                "speaker": "A",
                "speaker_id_global": "alex_hormozi",
                "speaker_name": "Alex Hormozi",
                "text": "Today I want to talk about pricing mistakes."
            },
            {
                "start": 72.0,
                "end": 80.0,
                "speaker": "B",
                "speaker_id_global": "guest_1",
                "speaker_name": "Guest",
                "text": "Yeah, I made that mistake too when I started."
            },
            {
                "start": 154.0,
                "end": 165.0,
                "speaker": "A",
                "speaker_id_global": "alex_hormozi",
                "speaker_name": "Alex Hormozi",
                "text": "Exactly, and here's why that happens."
            }
        ]
    }


def test_markdown_export_structure(sample_transcript, tmp_path):
    """Test that Markdown export has correct structure."""
    exporter = MarkdownExporter(artifacts_dir=str(tmp_path))
    markdown = exporter.export_episode(sample_transcript)

    # Check for YAML front matter
    assert markdown.startswith("---")
    assert 'episode_id: "ep-0042"' in markdown
    assert 'title: "Pricing Mistakes and Lessons"' in markdown
    assert 'date: "2025-09-10"' in markdown
    assert 'guest: "Alex Hormozi"' in markdown
    assert "duration: 2145" in markdown

    # Check for body content
    assert "# Episode 42 – Pricing Mistakes and Lessons" in markdown
    assert "## Transcript" in markdown
    assert '<audio controls src="https://cdn.example.com/audio/ep42.mp3"></audio>' in markdown

    # Check for transcript segments
    assert "**Alex Hormozi [00:05]:** Today I want to talk about pricing mistakes." in markdown
    assert "**Guest [01:12]:** Yeah, I made that mistake too when I started." in markdown
    assert "**Alex Hormozi [02:34]:** Exactly, and here's why that happens." in markdown


def test_speaker_extraction(sample_transcript):
    """Test that speakers are correctly extracted."""
    exporter = MarkdownExporter()
    speakers = exporter._extract_speakers(sample_transcript)

    assert len(speakers) == 2
    assert speakers[0]["id"] == "alex_hormozi"
    assert speakers[0]["display_name"] == "Alex Hormozi"
    assert speakers[1]["id"] == "guest_1"
    assert speakers[1]["display_name"] == "Guest"


def test_save_episode_artifacts(sample_transcript, tmp_path):
    """Test saving both JSON and Markdown artifacts."""
    exporter = MarkdownExporter(artifacts_dir=str(tmp_path))
    json_path, markdown_path = exporter.save_episode("ep-0042", sample_transcript)

    # Check paths exist
    assert json_path.exists()
    assert markdown_path.exists()

    # Check directory structure
    expected_dir = tmp_path / "episodes" / "ep-0042"
    assert expected_dir.exists()
    assert json_path == expected_dir / "transcript.json"
    assert markdown_path == expected_dir / "transcript.md"

    # Verify JSON content
    with open(json_path) as f:
        saved_json = json.load(f)
    assert saved_json["episode_id"] == "ep-0042"
    assert len(saved_json["segments"]) == 3

    # Verify Markdown content
    with open(markdown_path) as f:
        saved_markdown = f.read()
    assert "episode_id: \"ep-0042\"" in saved_markdown
    assert "Alex Hormozi" in saved_markdown


def test_episode_number_extraction():
    """Test extraction of episode numbers from titles."""
    exporter = MarkdownExporter()

    assert exporter._extract_episode_number("Episode 42 - Pricing") == "42"
    assert exporter._extract_episode_number("Ep 123: Growth Hacks") == "123"
    assert exporter._extract_episode_number("#7 - Customer Success") == "7"
    assert exporter._extract_episode_number("42 - The Answer") == "42"
    assert exporter._extract_episode_number("Random Title") is None


def test_timestamp_formatting():
    """Test that timestamps are correctly formatted."""
    exporter = MarkdownExporter()

    segment1 = {"start": 5, "speaker_name": "Alex", "text": "Hello"}
    assert exporter._format_segment(segment1) == "**Alex [00:05]:** Hello"

    segment2 = {"start": 125, "speaker_name": "Guest", "text": "Great point"}
    assert exporter._format_segment(segment2) == "**Guest [02:05]:** Great point"

    segment3 = {"start": 3661, "speaker_name": "Alex", "text": "Final thoughts"}
    assert exporter._format_segment(segment3) == "**Alex [61:01]:** Final thoughts"


def test_export_markdown_from_json_function(sample_transcript, tmp_path):
    """Test the convenience function for exporting."""
    json_path = tmp_path / "test.json"
    output_path = tmp_path / "test.md"

    # Save sample JSON
    with open(json_path, "w") as f:
        json.dump(sample_transcript, f)

    # Export to Markdown
    markdown = export_markdown_from_json(str(json_path), str(output_path))

    # Verify output
    assert output_path.exists()
    assert "episode_id: \"ep-0042\"" in markdown
    with open(output_path) as f:
        saved_content = f.read()
    assert saved_content == markdown