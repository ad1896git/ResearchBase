"""Centralized environment-backed Phase 1 configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from researchbase.persistence.database import DEFAULT_DATABASE_URL, database_url


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    artifact_store_root: str
    log_level: str
    application_env: str


def load_settings(environment: Mapping[str, str] | None = None) -> Settings:
    """Load the small Phase 1 configuration contract.

    An explicit mapping is used by tests and composition callers that already
    own their environment. The process environment keeps the historical
    ``database_url()`` override/default behavior.
    """

    values = os.environ if environment is None else environment
    log_level = values.get("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("LOG_LEVEL must be a standard logging level")
    application_env = values.get("APPLICATION_ENV", "development").strip()
    if not application_env:
        raise ValueError("APPLICATION_ENV must not be blank")
    artifact_store_root = values.get("ARTIFACT_STORE_ROOT", ".researchbase/artifacts").strip()
    if not artifact_store_root:
        raise ValueError("ARTIFACT_STORE_ROOT must not be blank")
    configured_database_url = (
        database_url() if environment is None else values.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    return Settings(configured_database_url, artifact_store_root, log_level, application_env)
