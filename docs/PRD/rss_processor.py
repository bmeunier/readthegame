"""
Filename: rss_processor.py

Description:
    RSS feed processing for podcast episodes in The Game Podcast ETL Pipeline.
    Handles fetching and parsing RSS feeds, extracting episode metadata,
    audio URLs, and filtering rerun episodes based on configurable keywords.

Usage:
    from askthegame.audio.rss_processor import RSSProcessor
    
    processor = RSSProcessor()
    episodes = processor.fetch_episodes("https://feeds.example.com/podcast.xml")
    is_rerun = processor.is_rerun_episode("Throwback: Episode 5")

Author: Benoit Meunier
Created: 2025-06-26
Last Updated: 2025-06-26
"""

import logging
import feedparser
import re
from typing import List, Optional

from ..utils.models import EpisodeMetadata
from ..utils.config import config
from ..utils.guid_normalizer import GUIDNormalizer


class RSSProcessor:
    """Processes RSS feeds to extract episode metadata."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pipeline_config = config.load_pipeline_config()
    
    def fetch_episodes(self, feed_url: str) -> List[EpisodeMetadata]:
        """Fetch episodes with normalized GUIDs and validation."""
        self.logger.info(f"Fetching episodes from RSS feed: {feed_url}")
        
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            self.logger.warning("No entries found in RSS feed")
            return []
        
        episodes = []
        skipped_count = 0
        invalid_guid_count = 0
        
        for entry in feed.entries:
            try:
                # Extract and validate GUID
                raw_guid = entry.get('id', '')
                if not raw_guid:
                    self.logger.warning(f"Episode missing ID: {entry.get('title', 'Unknown')}")
                    skipped_count += 1
                    continue
                
                # Normalize GUID
                try:
                    normalized_guid = GUIDNormalizer.normalize(raw_guid)
                except ValueError as e:
                    self.logger.error(f"Invalid GUID '{raw_guid}' for episode '{entry.get('title', 'Unknown')}': {e}")
                    invalid_guid_count += 1
                    continue
                
                # Extract audio URL
                audio_url = self._extract_audio_url(entry)
                if not audio_url:
                    self.logger.debug(f"No audio URL found for episode: {entry.get('title', 'Unknown')}")
                    skipped_count += 1
                    continue
                
                # Validate audio URL
                if not self._validate_audio_url(audio_url):
                    self.logger.warning(f"Invalid audio URL for episode: {entry.get('title', 'Unknown')}")
                    skipped_count += 1
                    continue
                
                # Create episode metadata
                episode = EpisodeMetadata(
                    guid=normalized_guid,  # ✅ Now normalized
                    title=entry.get('title', 'No Title').strip(),
                    publish_date=entry.get('published', ''),
                    audio_url=audio_url,
                    episode_number=self._extract_episode_number(entry),
                    description=entry.get('description', ''),
                    duration=self._extract_duration(entry)
                )
                
                episodes.append(episode)
                
            except Exception as e:
                self.logger.error(f"Error processing RSS entry: {e}", exc_info=True)
                skipped_count += 1
                continue
        
        # Log processing summary
        self.logger.info(f"RSS processing complete:")
        self.logger.info(f"  ✅ Episodes extracted: {len(episodes)}")
        self.logger.info(f"  ⚠️  Episodes skipped: {skipped_count}")
        self.logger.info(f"  ❌ Invalid GUIDs: {invalid_guid_count}")
        
        return episodes
    
    def _extract_audio_url(self, entry) -> Optional[str]:
        """Extract audio URL from RSS entry."""
        if not hasattr(entry, 'enclosures'): 
            return None
        
        for enc in entry.enclosures:
            if hasattr(enc, 'type') and 'audio' in enc.type.lower(): 
                return enc.href
        
        return None
    
    def _validate_audio_url(self, url: str) -> bool:
        """Validate audio URL format and accessibility."""
        if not url:
            return False
        
        # Basic URL validation - now supports file:// URLs for local RSS
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('file://')):
            return False
        
        # Check for audio file extensions
        audio_extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.aac']
        if not any(ext in url.lower() for ext in audio_extensions):
            self.logger.debug(f"Audio URL may not contain valid audio extension: {url}")
        
        return True
    
    def _extract_episode_number(self, entry) -> Optional[int]:
        """Extract episode number from various sources."""
        # Try iTunes episode field first
        episode_num = entry.get('itunes_episode')
        if episode_num and str(episode_num).isdigit():
            return int(episode_num)
        
        # Try to extract from title
        title = entry.get('title', '')
        match = re.search(r'Ep\s*(\d+)', title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_duration(self, entry) -> Optional[int]:
        """Extract episode duration in seconds."""
        duration = entry.get('itunes_duration')
        if duration:
            try:
                # Handle various duration formats
                if ':' in str(duration):
                    parts = str(duration).split(':')
                    if len(parts) == 2:  # MM:SS
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # HH:MM:SS
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    return int(duration)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def is_rerun_episode(self, title: str) -> bool:
        """Check if episode is a rerun based on title keywords."""
        rerun_keywords = self.pipeline_config['rerun_keywords']
        return any(keyword in title.lower() for keyword in rerun_keywords)