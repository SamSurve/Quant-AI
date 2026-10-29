"""Minimal structured operational logging with secret redaction and privacy preservation."""

from __future__ import annotations

import logging
import re
from typing import Any

LOGGER = logging.getLogger("quantai.research")

_SECRET_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+)[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key[\s:=]+)[a-zA-Z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"://([^:]+):([^@]+)@", re.IGNORECASE),
]

_EXCLUDED_KEYS = frozenset({
    "prompt",
    "response",
    "api_key",
    "authorization",
    "auth",
    "token",
    "secret",
    "credentials",
    "password",
    "raw_key",
})


def scrub_secrets(val: Any) -> Any:
    """Scrub potential credentials and API keys from values before logging or display."""
    if isinstance(val, str):
        redacted = val
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return redacted
    if isinstance(val, dict):
        return {
            k: scrub_secrets(v)
            for k, v in val.items()
            if k.lower() not in _EXCLUDED_KEYS
        }
    if isinstance(val, (list, tuple)):
        return [scrub_secrets(item) for item in val]
    return val


def log_research_event(event: str, **fields: Any) -> None:
    """Log structured research event with sensitive fields dropped and string values scrubbed."""
    safe_fields = {
        key: scrub_secrets(value)
        for key, value in fields.items()
        if key.lower() not in _EXCLUDED_KEYS
    }
    LOGGER.info("research_event=%s fields=%s", event, safe_fields)
