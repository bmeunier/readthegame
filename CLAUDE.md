# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Read The Game is a podcast transcription pipeline that creates speaker-aware transcripts with audio sync. The project processes audio from "The Game" podcast by Alex Hormozi, using advanced diarization and speaker recognition to create searchable, structured documents.

## Commands

### Development Setup
```bash
# Install dependencies
make setup-dev
# Or directly:
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
make test
# Or directly:
pytest tests/

# Run specific test file
pytest tests/test_transcription.py

# Run with verbose output
pytest -v tests/
```

### Running the Pipeline
```bash
# Main pipeline entry point
python src/main.py
```

### Code Quality
```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/
```

## Architecture

The project follows a multi-stage ETL pipeline architecture:

1. **Audio Ingestion**: Handles audio file input (MP3/WAV) with future RSS feed support
2. **Diarization & ASR**: Uses pyannote-audio Precision-2 for speaker diarization and Whisper/Deepgram for transcription
3. **Speaker Memory**: Implements ECAPA-based embeddings for persistent speaker identification across episodes
4. **Indexing & Storage**: Uses Supabase pgvector initially, with plans to migrate to Qdrant

### Key Components

- **Pipeline Stage Pattern**: Each processing stage (`src/pipeline/`) is isolated with checkpointing for fault tolerance
- **Speaker Identification**: Cross-episode speaker memory using ECAPA embeddings with temporal boosting and drift tracking
- **Confidence Filtering**: Optional filtering based on ASR confidence (< 0.85) and ECAPA similarity (< 0.75)

### Directory Structure

- `src/pipeline/`: Core processing stages (transcription, diarization, speaker memory, output)
- `src/models/`: Data models (transcript, episode, speaker, config schema)
- `src/utils/`: Helper utilities (audio tools, file operations, logging, timing)
- `tests/`: Test suite with fixtures for each pipeline component
- `vercel_frontend/`: Static frontend for displaying transcripts (HTML/CSS)
- `docs/`: Project documentation (PRD, technical specs, setup guides)

## Key Technologies

- **Diarization**: pyannote-audio 3.3.2 with Precision-2 model
- **Speech Recognition**: Whisper (local) with Deepgram SDK fallback
- **Speaker Embeddings**: ECAPA-TDNN via SpeechBrain
- **Vector Storage**: Supabase pgvector (future: Qdrant/Weaviate)
- **ML Framework**: PyTorch with Lightning for training pipelines
- **Testing**: pytest with asyncio support

## Important Considerations

- The pipeline uses checkpointing at each stage stored in `job_state.json`
- Speaker profiles are persisted with embeddings for cross-episode identification
- Temporal boosting formula: `adjusted_score = base_score * (1 / (1 + log1p(days_since_last)))`
- The project is designed for "The Game" podcast but architecture supports any podcast feed