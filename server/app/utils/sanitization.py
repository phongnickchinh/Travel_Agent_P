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


def sanitize_user_input(data: Dict[str, Any], allowed_keys: List[str]) -> Dict[str, Any]:
    """Keep only allowed keys and sanitize string values by removing newlines and trimming length.

    - Remove keys not in allowed_keys
    - Truncate string values to 500 chars by default (avoid huge payloads)
    - Remove newlines and stray control characters
    """
    if not isinstance(data, dict):
        return {}

    sanitized: Dict[str, Any] = {}
    for k in allowed_keys:
        if k in data:
            v = data[k]
            if isinstance(v, str):
                # Strip control chars and limit length
                s = re.sub(r"[\x00-\x1F\x7F\r\n\t]", " ", v)
                sanitized[k] = s[:500]
            elif isinstance(v, list):
                # Keep only primitives and strings truncated
                cleaned_list = []
                for item in v:
                    if _is_primitive(item):
                        if isinstance(item, str):
                            item = re.sub(r"[\x00-\x1F\x7F\r\n\t]", " ", item)[:200]
                        cleaned_list.append(item)
                sanitized[k] = cleaned_list
            elif isinstance(v, dict):
                # Shallow sanitize nested dictionaries
                nested = {nk: nv for nk, nv in v.items() if _is_primitive(nv)}
                sanitized[k] = nested
            elif _is_primitive(v):
                sanitized[k] = v
            else:
                # Unsupported types are skipped
                continue

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
