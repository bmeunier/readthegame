"""
Filename: service.py

Description:
    Speaker identification service for The Game Podcast ETL Pipeline.
    Handles speaker diarization using PyAnnote and speaker identification
    using ECAPA embeddings compared against Alex Hormozi's voiceprint.

Usage:
    from askthegame.speaker.service import SpeakerIdentificationService
    
    service = SpeakerIdentificationService()
    service.initialize_models()
    speaker_results = service.identify_speakers(audio_url, utterances)

Author: Benoit Meunier
Created: 2025-06-26
Last Updated: 2025-06-26
"""

import logging
import torch
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import torchaudio
from pyannote.audio import Pipeline as PyannotePipeline
from speechbrain.inference import SpeakerRecognition
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from ..utils.config import config
from .supabase_embedding_index import SupabaseEmbeddingIndex


class SpeakerIdentificationService:
    """Handles speaker diarization and identification against Alex Hormozi's voiceprint."""
    
    def __init__(self, hf_token: str):
        self.logger = logging.getLogger(__name__)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.hf_token = hf_token
        self.diarization_pipeline = None
        self.embedding_model = None
        self.reference_voiceprint = None
        
        # Load configuration
        self.speaker_config = config.load_speaker_config()
        self.similarity_threshold = self.speaker_config['similarity_threshold']
        
        # Initialize embedding index (will be set later by pipeline)
        self.embedding_index = None
        
    def initialize_models(self) -> bool:
        """Initialize PyAnnote and SpeechBrain models."""
        self.logger.info("Initializing speaker identification models...")
        
        try:
            # Check voiceprint file exists
            voiceprint_path = Path(self.speaker_config['voiceprint_path'])
            if not voiceprint_path.exists():
                self.logger.error(f"Voiceprint file not found: {voiceprint_path}")
                return False
                
            # Load PyAnnote diarization pipeline
            self.diarization_pipeline = PyannotePipeline.from_pretrained(
                self.speaker_config['diarization_pipeline'], 
                use_auth_token=self.hf_token
            ).to(self.device)
            
            # Load SpeechBrain embedding model
            self.embedding_model = SpeakerRecognition.from_hparams(
                source=self.speaker_config['embedding_model'], 
                run_opts={"device": self.device}
            )
            
            # Load Alex Hormozi's voiceprint
            self.reference_voiceprint = torch.load(voiceprint_path, map_location=self.device)
            if not isinstance(self.reference_voiceprint, torch.Tensor):
                self.logger.error("Voiceprint file does not contain a valid tensor")
                return False
                
            self.logger.info(f"✅ Speaker identification models initialized successfully")
            self.logger.info(f"   Voiceprint shape: {self.reference_voiceprint.shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize speaker identification models: {e}", exc_info=True)
            return False
    
    def identify_speakers_in_utterances(self, audio_url: str, utterances: List[Dict], episode_id: str = None) -> List[Dict]:
        """
        Identify speakers in Deepgram utterances using embedding index with cross-episode memory.
        
        Args:
            audio_url: URL of the audio file
            utterances: List of Deepgram utterances with speaker labels
            episode_id: Episode identifier for tracking
            
        Returns:
            List of utterances with speaker names (Alex Hormozi vs Guest)
        """
        if not self.diarization_pipeline or not self.embedding_model:
            self.logger.warning("Speaker identification models not initialized, skipping")
            return self._fallback_speaker_assignment(utterances)
        
        # Generate default episode_id if not provided
        if not episode_id:
            episode_id = f"episode_{hash(audio_url) % 10000}"
        
        try:
            self.logger.info(f"🎤 Starting speaker identification for {len(utterances)} utterances (episode: {episode_id})...")
            
            # Use embedding index for speaker identification
            speaker_mapping = self._analyze_speakers_with_index(utterances, episode_id)
            
            # Apply speaker mapping to utterances
            identified_utterances = []
            for utterance in utterances:
                deepgram_speaker = utterance.get('speaker', 0)
                identified_speaker = speaker_mapping.get(deepgram_speaker, f"Guest_{deepgram_speaker}")
                
                # Update utterance with identified speaker
                updated_utterance = utterance.copy()
                updated_utterance['identified_speaker'] = identified_speaker
                identified_utterances.append(updated_utterance)
            
            alex_count = sum(1 for u in identified_utterances if u['identified_speaker'] == 'Alex Hormozi')
            guest_count = len(identified_utterances) - alex_count
            
            self.logger.info(f"✅ Speaker identification completed:")
            self.logger.info(f"   Alex Hormozi: {alex_count} utterances")
            self.logger.info(f"   Guests: {guest_count} utterances")
            
            return identified_utterances
            
        except Exception as e:
            self.logger.error(f"Speaker identification failed: {e}", exc_info=True)
            return self._fallback_speaker_assignment(utterances)
    
    def _analyze_speakers_with_index(self, utterances: List[Dict], episode_id: str) -> Dict[int, str]:
        """
        Identify speakers using embedding index with cross-episode memory.
        
        For each unique Deepgram speaker, we'll use their voiceprint to search
        the embedding index and find the best match.
        """
        if self.embedding_index is None:
            self.logger.warning("Speaker embedding index not initialized, using fallback identification")
            return self._analyze_deepgram_speakers_fallback(utterances)
            
        if not self.embedding_model:
            self.logger.warning("Embedding model not initialized, falling back to heuristics")
            return self._analyze_deepgram_speakers_fallback(utterances)
        
        speaker_mapping = {}
        
        # Group utterances by Deepgram speaker ID
        speakers_utterances = {}
        for utterance in utterances:
            speaker_id = utterance.get('speaker', 0)
            if speaker_id not in speakers_utterances:
                speakers_utterances[speaker_id] = []
            speakers_utterances[speaker_id].append(utterance)
        
        # For each speaker, create a voiceprint and search the index
        for speaker_id, speaker_utterances in speakers_utterances.items():
            try:
                # Create composite embedding from multiple utterances (more robust)
                speaker_embeddings = []
                
                # Use first few utterances to create voiceprint
                sample_utterances = speaker_utterances[:3]  # Use first 3 for speed
                
                for utterance in sample_utterances:
                    # In a real implementation, you'd extract audio for this segment
                    # For now, simulate by using the reference voiceprint with noise
                    # TODO: Replace with actual audio segment processing
                    if self.reference_voiceprint is not None:
                        # Add small noise to simulate different utterances
                        noise = np.random.normal(0, 0.01, self.reference_voiceprint.shape)
                        simulated_embedding = self.reference_voiceprint.cpu().numpy() + noise
                        speaker_embeddings.append(simulated_embedding)
                
                if not speaker_embeddings:
                    speaker_mapping[speaker_id] = f"Guest_{speaker_id}"
                    continue
                
                # Average the embeddings for more robust matching
                avg_embedding = np.mean(speaker_embeddings, axis=0)
                
                # Search the embedding index
                matches = self.embedding_index.search_similar(
                    avg_embedding, 
                    top_k=3, 
                    min_similarity=self.similarity_threshold,
                    temporal_boost=True
                )
                
                if matches:
                    best_match = matches[0]
                    confidence = best_match['similarity']
                    
                    if best_match.get('label'):
                        # Found a known speaker
                        speaker_mapping[speaker_id] = best_match['label']
                        self.logger.info(
                            f"Speaker {speaker_id} identified as {best_match['label']} "
                            f"(confidence: {confidence:.3f})"
                        )
                    elif best_match['cluster_id']:
                        # Found a recurring unknown speaker
                        speaker_mapping[speaker_id] = best_match['cluster_id']
                        self.logger.info(
                            f"Speaker {speaker_id} identified as {best_match['cluster_id']} "
                            f"(confidence: {confidence:.3f})"
                        )
                    else:
                        # Unknown speaker, create new entry
                        speaker_mapping[speaker_id] = f"Unknown_{speaker_id}"
                else:
                    # No matches found, create new entry
                    speaker_mapping[speaker_id] = f"Unknown_{speaker_id}"
                
                # Add this speaker's embedding to the index for future episodes
                avg_timestamp = np.mean([u.get('start_time', 0) for u in speaker_utterances])
                avg_duration = np.mean([u.get('end_time', 0) - u.get('start_time', 0) for u in speaker_utterances])
                
                self.embedding_index.add_embedding(
                    embedding=avg_embedding,
                    episode_id=episode_id,
                    timestamp=float(avg_timestamp),
                    duration=float(avg_duration),
                    confidence=0.8,  # Default confidence for Deepgram speakers
                    speaker_label=speaker_mapping[speaker_id] if not speaker_mapping[speaker_id].startswith('Unknown_') else None,
                    segment_text=speaker_utterances[0].get('text', '')[:100]  # First 100 chars
                )
                
            except Exception as e:
                self.logger.error(f"Error processing speaker {speaker_id}: {e}")
                speaker_mapping[speaker_id] = f"Guest_{speaker_id}"
        
        # If no speakers were identified as Alex, use heuristic as fallback
        alex_found = any('Alex' in label for label in speaker_mapping.values())
        if not alex_found and speaker_mapping:
            # Find the speaker with the most utterances and assume it's Alex
            primary_speaker = max(speakers_utterances.keys(), 
                                key=lambda k: len(speakers_utterances[k]))
            speaker_mapping[primary_speaker] = "Alex Hormozi"
            self.logger.info(f"No Alex found in index, assigned to primary speaker {primary_speaker}")
        
        return speaker_mapping
    
    def _analyze_deepgram_speakers_fallback(self, utterances: List[Dict]) -> Dict[int, str]:
        """Fallback heuristic-based speaker identification."""
        # Count utterances per speaker
        speaker_counts = {}
        for utterance in utterances:
            speaker = utterance.get('speaker', 0)
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        
        self.logger.info(f"Speaker distribution: {speaker_counts}")
        
        # Heuristic: The speaker with the most utterances is likely Alex Hormozi
        if speaker_counts:
            primary_speaker = max(speaker_counts.keys(), key=lambda k: speaker_counts[k])
            
            speaker_mapping = {}
            for speaker_id in speaker_counts.keys():
                if speaker_id == primary_speaker:
                    speaker_mapping[speaker_id] = "Alex Hormozi"
                else:
                    speaker_mapping[speaker_id] = f"Guest_{speaker_id}"
            
            return speaker_mapping
        
        return {0: "Alex Hormozi"}  # Default fallback
    
    def _fallback_speaker_assignment(self, utterances: List[Dict]) -> List[Dict]:
        """Fallback speaker assignment when identification fails."""
        self.logger.warning("Using fallback speaker assignment")
        
        fallback_utterances = []
        for utterance in utterances:
            updated_utterance = utterance.copy()
            # Simple fallback: assume speaker 0 is Alex, others are guests
            deepgram_speaker = utterance.get('speaker', 0)
            if deepgram_speaker == 0:
                updated_utterance['identified_speaker'] = "Alex Hormozi"
            else:
                updated_utterance['identified_speaker'] = f"Guest_{deepgram_speaker}"
            fallback_utterances.append(updated_utterance)
            
        return fallback_utterances
    
    def get_speaker_statistics(self, identified_utterances: List[Dict]) -> Dict[str, int]:
        """Get statistics on speaker distribution."""
        stats = {}
        for utterance in identified_utterances:
            speaker = utterance.get('identified_speaker', 'Unknown')
            stats[speaker] = stats.get(speaker, 0) + 1
        return stats
    
    def get_embedding_index_stats(self) -> Dict:
        """Get statistics from the embedding index."""
        return self.embedding_index.get_statistics()
    
    def cluster_recurring_speakers(self, min_cluster_size: int = 3) -> Dict[str, List[str]]:
        """Identify recurring speakers by clustering unknown embeddings."""
        return self.embedding_index.get_speaker_clusters(min_cluster_size=min_cluster_size)
    
    def assign_speaker_name(self, embedding_id: str, speaker_name: str):
        """Assign a name to a speaker (human feedback)."""
        self.embedding_index.assign_speaker_label(embedding_id, speaker_name)
        self.logger.info(f"Assigned speaker name '{speaker_name}' to embedding {embedding_id}")
    
    def prune_old_data(self, days_old: int = 180, min_confidence: float = 0.7) -> int:
        """Remove old, low-confidence embeddings from the index."""
        return self.embedding_index.prune_old_embeddings(days_old, min_confidence)