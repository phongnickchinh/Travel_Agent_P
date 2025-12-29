"""
Text Utilities
==============

Purpose:
- Text normalization functions
- Accent removal for search
- Unicode handling

Author: Travel Agent P Team
Date: December 2025
"""

import re
import unicodedata
from typing import Optional

try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False


def remove_accents(text: str) -> str:
    """
    Remove accents/diacritics from text.
    
    Uses unidecode if available, falls back to unicode normalization.
    
    Args:
        text: Input text (e.g., "Đà Nẵng")
        
    Returns:
        Unaccented text (e.g., "Da Nang")
        
    Example:
        >>> remove_accents("Đà Nẵng")
        "Da Nang"
        >>> remove_accents("Hồ Chí Minh")
        "Ho Chi Minh"
    """
    if not text:
        return ""
    
    if HAS_UNIDECODE:
        return unidecode(text)
    
    # Fallback: Unicode normalization (less accurate for Vietnamese)
    # NFD: decompose characters (e.g., ñ → n + ̃)
    normalized = unicodedata.normalize('NFD', text)
    # Remove combining characters (diacritics)
    without_diacritics = ''.join(
        char for char in normalized
        if unicodedata.category(char) != 'Mn'
    )
    
    # Special handling for Vietnamese characters not covered by NFD
    vietnamese_map = {
        'đ': 'd', 'Đ': 'D',
    }
    for vn_char, ascii_char in vietnamese_map.items():
        without_diacritics = without_diacritics.replace(vn_char, ascii_char)
    
    return without_diacritics


def normalize_for_search(text: str) -> str:
    """
    Normalize text for search indexing.
    
    - Lowercase
    - Remove accents
    - Remove special characters
    - Collapse whitespace
    
    Args:
        text: Input text
        
    Returns:
        Normalized search text
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove accents
    text = remove_accents(text)
    
    # Remove special characters (keep alphanumeric and space)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    Generate URL-safe slug from text.
    
    Args:
        text: Input text
        max_length: Maximum slug length
        
    Returns:
        URL-safe slug
        
    Example:
        >>> generate_slug("Bãi biển Mỹ Khê")
        "bai-bien-my-khe"
    """
    if not text:
        return ""
    
    # Normalize
    slug = normalize_for_search(text)
    
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Truncate
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]
    
    return slug.strip('-')


def extract_keywords(text: str, min_length: int = 2) -> list:
    """
    Extract searchable keywords from text.
    
    Args:
        text: Input text
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    normalized = normalize_for_search(text)
    words = normalized.split()
    
    return [w for w in words if len(w) >= min_length]
