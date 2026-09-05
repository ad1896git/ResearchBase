"""Small JSON event writer for the Phase 1 command boundary."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from time import monotonic
from typing import Any

logger = logging.getLogger("researchbase.commands")


def emit_event(event: str, fields: Mapping[str, Any]) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")))


def elapsed(start: float) -> float:
    return round(monotonic() - start, 6)
