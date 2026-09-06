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
