"""
Input sanitization utilities
=============================

Purpose:
- Sanitize request JSON payloads to prevent NoSQL injection and prompt injection.
- Provide helper `sanitize_user_input` that keeps only allowed fields and normalizes strings.
- Provide `contains_mongo_operators` to detect forbidden MongoDB operators.

Author: GitHub Copilot
"""

from typing import Any, Dict, List
import re


MONGO_OPERATOR_PREFIX = "$"


def _is_primitive(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None)))


def contains_mongo_operators(obj: Any) -> bool:
    """Recursively check if the data contains MongoDB operators (keys starting with $).

    This is a conservative check – it will flag nested dicts that are potentially
    used for injection.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                if k.startswith(MONGO_OPERATOR_PREFIX) or "." in k:
                    return True
            if contains_mongo_operators(v):
                return True
        return False
    elif isinstance(obj, list):
        for item in obj:
            if contains_mongo_operators(item):
                return True
        return False
    else:
        return False


def _deep_sanitize_value(value: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
    """
    Recursively sanitize a value while preserving structure.
    
    - Sanitize strings (remove control chars, limit length)
    - Preserve lists and dicts structure
    - Prevent infinite recursion with max_depth
    
    Args:
        value: Value to sanitize
        max_depth: Maximum recursion depth (default 5)
        current_depth: Current recursion level
        
    Returns:
        Sanitized value with preserved structure
    """
    # Prevent infinite recursion
    if current_depth > max_depth:
        return None
    
    if isinstance(value, str):
        # Sanitize string: remove control chars, limit length
        sanitized = re.sub(r"[\x00-\x1F\x7F\r\n\t]", " ", value)
        # Shorter limit for nested values to prevent huge payloads
        max_len = 500 if current_depth == 0 else 200
        return sanitized[:max_len]
    
    elif isinstance(value, list):
        # Recursively sanitize each item in list
        return [
            _deep_sanitize_value(item, max_depth, current_depth + 1)
            for item in value
        ]
    
    elif isinstance(value, dict):
        # Recursively sanitize each value in dict
        return {
            k: _deep_sanitize_value(v, max_depth, current_depth + 1)
            for k, v in value.items()
        }
    
    elif _is_primitive(value):
        # Keep primitives as-is (int, float, bool, None)
        return value
    
    else:
        # Unsupported types (objects, functions, etc.)
        return None


def sanitize_user_input(data: Dict[str, Any], allowed_keys: List[str]) -> Dict[str, Any]:
    """Keep only allowed keys and deeply sanitize all values while preserving structure.

    - Remove keys not in allowed_keys
    - Recursively sanitize strings (remove control chars, limit length)
    - Preserve nested lists and dicts structure
    - Support complex structures like itinerary_updates
    
    Args:
        data: Input dictionary
        allowed_keys: List of allowed top-level keys
        
    Returns:
        Sanitized dictionary with only allowed keys
    """
    if not isinstance(data, dict):
        return {}

    sanitized: Dict[str, Any] = {}
    for k in allowed_keys:
        if k in data:
            v = data[k]
            # Deep sanitize value while preserving structure
            sanitized[k] = _deep_sanitize_value(v)

    return sanitized


def escape_for_prompt(text: str, max_length: int = 200) -> str:
    """Escape user-provided text for inclusion in prompts.

    - Remove control characters and newlines
    - Limit length
    - Remove suspicious substrings like 'IGNORE ALL PREVIOUS INSTRUCTIONS'
    """
    if not isinstance(text, str):
        return ""
    s = re.sub(r"[\x00-\x1F\x7F]", " ", text)
    s = s.replace('\n', ' ').replace('\r', ' ')
    s = s.strip()
    # Remove possible prompt injection phrases
    s = re.sub(r"IGNORE ALL PREVIOUS INSTRUCTIONS|DISREGARD.*INSTRUCTIONS", "", s, flags=re.IGNORECASE)
    return s[:max_length]
