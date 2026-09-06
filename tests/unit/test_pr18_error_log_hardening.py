from __future__ import annotations

import json
import logging

from researchbase.foundation.structured_logging import emit_event


def test_structured_logging_redacts_nested_credentials_and_connection_strings_checked(
    caplog,
) -> None:
    with caplog.at_level(logging.INFO, logger="researchbase.commands"):
        emit_event(
            "pr18.audit",
            {
                "result": "failure",
                "database_url": "postgresql://user:super-secret@db:5432/researchbase",
                "nested": {"password": "pw-value", "safe": "ok"},
                "messages": ["token=abc123", "credential: xyz"],
            },
        )

    payload = json.loads(caplog.records[-1].message)
    rendered = json.dumps(payload, sort_keys=True)
    assert "super-secret" not in rendered
    assert "pw-value" not in rendered
    assert "abc123" not in rendered
    assert "xyz" not in rendered
    assert payload["database_url"] == "[REDACTED]"
    assert payload["nested"]["password"] == "[REDACTED]"


def test_structured_logging_redacts_api_keys_authorization_bearer_and_exception_secrets(
    caplog,
) -> None:
    with caplog.at_level(logging.INFO, logger="researchbase.commands"):
        emit_event(
            "pr18.redaction.attack",
            {
                "result": "failure",
                "safe_context": "request-123",
                "api_key": "api-secret-123",
                "secret": "field-secret-321",
                "Authorization": "Bearer auth-secret-456",
                "nested": {
                    "access_token": "access-secret-789",
                    "exception": "psycopg://user:dsn-secret@db:5432/researchbase",
                },
                "message": "Bearer message-secret-999",
            },
        )

    payload = json.loads(caplog.records[-1].message)
    rendered = json.dumps(payload, sort_keys=True)
    assert payload["safe_context"] == "request-123"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["secret"] == "[REDACTED]"
    assert payload["Authorization"] == "[REDACTED]"
    assert payload["nested"]["access_token"] == "[REDACTED]"
    assert "api-secret-123" not in rendered
    assert "field-secret-321" not in rendered
    assert "auth-secret-456" not in rendered
    assert "access-secret-789" not in rendered
    assert "dsn-secret" not in rendered
    assert "message-secret-999" not in rendered
