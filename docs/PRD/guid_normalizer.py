"""
GUID Normalization Utilities

Handles inconsistent UUID formats from RSS feeds and database storage.
Ensures all GUIDs are consistently formatted as 36-character UUIDs.
"""

import re
import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GUIDNormalizer:
    """Centralized GUID normalization and validation."""
    
    # Standard UUID regex (36 chars with hyphens)
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # Compact UUID regex (32 chars without hyphens)  
    COMPACT_UUID_PATTERN = re.compile(r'^[0-9a-f]{32}$', re.IGNORECASE)
    
    @staticmethod
    def normalize(guid: str) -> str:
        """
        Convert any valid GUID format to standard 36-character UUID.
        
        Args:
            guid: Input GUID in any valid format
            
        Returns:
            Normalized 36-character UUID string
            
        Raises:
            ValueError: If GUID format is invalid
        """
        if not guid:
            raise ValueError("GUID cannot be empty")
        
        guid = str(guid).strip().lower()
        
        # Already normalized
        if GUIDNormalizer.UUID_PATTERN.match(guid):
            return guid
        
        # Compact format - add hyphens
        if GUIDNormalizer.COMPACT_UUID_PATTERN.match(guid):
            return f"{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:]}"
        
        # Try to extract valid UUID from mixed format
        clean = re.sub(r'[^0-9a-f]', '', guid, flags=re.IGNORECASE)
        if len(clean) == 32 and GUIDNormalizer.COMPACT_UUID_PATTERN.match(clean):
            return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
        
        raise ValueError(f"Invalid GUID format: {guid}")
    
    @staticmethod
    def validate(guid: str) -> bool:
        """
        Validate if a string is a valid GUID in any supported format.
        
        Args:
            guid: Input string to validate
            
        Returns:
            True if valid GUID format, False otherwise
        """
        try:
            GUIDNormalizer.normalize(guid)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def generate() -> str:
        """Generate a new normalized UUID."""
        return str(uuid.uuid4()).lower()
    
    @staticmethod
    def equals(guid1: str, guid2: str) -> bool:
        """
        Compare two GUIDs for equality, handling format differences.
        
        Args:
            guid1: First GUID to compare
            guid2: Second GUID to compare
            
        Returns:
            True if GUIDs represent the same UUID
        """
        try:
            return GUIDNormalizer.normalize(guid1) == GUIDNormalizer.normalize(guid2)
        except ValueError:
            return False