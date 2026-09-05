"""Centralized environment-backed Phase 1 configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from researchbase.persistence.database import database_url


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    artifact_store_root: str
    log_level: str
    application_env: str


def load_settings() -> Settings:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("LOG_LEVEL must be a standard logging level")
    application_env = os.getenv("APPLICATION_ENV", "development").strip()
    if not application_env:
        raise ValueError("APPLICATION_ENV must not be blank")
    artifact_store_root = os.getenv("ARTIFACT_STORE_ROOT", ".researchbase/artifacts").strip()
    if not artifact_store_root:
        raise ValueError("ARTIFACT_STORE_ROOT must not be blank")
    return Settings(database_url(), artifact_store_root, log_level, application_env)
