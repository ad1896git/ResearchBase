from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest

from researchbase.foundation.structured_logging import (
    configure_logging,
    emit_application_event,
    emit_event,
    logger,
)
from researchbase.persistence.config import load_settings


def test_settings_accept_explicit_environment_and_preserve_database_override() -> None:
    settings = load_settings(
        {
            "DATABASE_URL": "postgresql+psycopg://example/database",
            "LOG_LEVEL": "DEBUG",
            "APPLICATION_ENV": "test",
            "ARTIFACT_STORE_ROOT": "/tmp/researchbase-artifacts",
        }
    )

    assert settings.database_url == "postgresql+psycopg://example/database"
    assert settings.log_level == "DEBUG"
    assert settings.application_env == "test"
    assert settings.artifact_store_root == "/tmp/researchbase-artifacts"


def test_settings_use_frozen_defaults_and_reject_blank_environment() -> None:
    settings = load_settings({})
    assert settings.application_env == "development"
    assert settings.artifact_store_root == ".researchbase/artifacts"

    with pytest.raises(ValueError, match="APPLICATION_ENV"):
        load_settings({"APPLICATION_ENV": "   "})


def test_application_logging_has_required_context_and_no_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_logging("DEBUG", "test")
    request_id = uuid4()
    actor_id = uuid4()
    project_id = uuid4()
    target_id = uuid4()

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        emit_application_event(
            command_name="create_project",
            request_id=request_id,
            correlation_id=None,
            actor_id=actor_id,
            project_id=project_id,
            target_id=target_id,
            result="failure",
            error_code="VALIDATION_ERROR",
            duration_ms=2.5,
            rollback=True,
        )

    payload = json.loads(caplog.records[-1].message)
    assert {
        "timestamp",
        "level",
        "request_id",
        "correlation_id",
        "command_name",
        "actor_id",
        "project_id",
        "target_id",
        "result",
        "error_code",
        "duration_ms",
        "rollback",
        "application_env",
    } <= set(payload)
    assert payload["request_id"] == str(request_id)
    assert payload["actor_id"] == str(actor_id)
    assert payload["project_id"] == str(project_id)
    assert payload["target_id"] == str(target_id)
    assert payload["application_env"] == "test"
    assert "DATABASE_URL" not in caplog.text
    assert "password" not in caplog.text.lower()
    assert "token" not in caplog.text.lower()
    assert logger.level == logging.DEBUG


def test_legacy_event_logging_redacts_credential_bearing_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_logging("INFO", "test")
    with caplog.at_level(logging.INFO, logger=logger.name):
        emit_event(
            "command",
            {
                "DATABASE_URL": "postgresql+psycopg://user:secret@db/researchbase",
                "password": "secret-password",
                "token": "secret-token",
                "nested": {"credentials": "secret-credentials"},
            },
        )

    assert "secret" not in caplog.text
    payload = json.loads(caplog.records[-1].message)
    assert payload["DATABASE_URL"] == "[REDACTED]"
    assert payload["password"] == "[REDACTED]"
    assert payload["token"] == "[REDACTED]"
    assert payload["nested"]["credentials"] == "[REDACTED]"
