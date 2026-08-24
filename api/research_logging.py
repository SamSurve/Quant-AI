"""Minimal structured operational logging with no prompt, response, or secret values."""

from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger("quantai.research")


def log_research_event(event: str, **fields: Any) -> None:
    safe_fields = {key: value for key, value in fields.items() if key not in {"prompt", "response", "api_key", "authorization"}}
    LOGGER.info("research_event=%s fields=%s", event, safe_fields)
