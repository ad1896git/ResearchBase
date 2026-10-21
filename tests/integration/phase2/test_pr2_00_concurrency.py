from __future__ import annotations

import os

import pytest

from tests.integration.phase2.test_pr2_00_challenges import (
    _challenge_consumers_have_one_winner,
    _challenge_expiry_after_required_lock_wait_is_denied,
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment,
)


def test_challenge_single_winner(phase2_database_url: str) -> None:
    _challenge_consumers_have_one_winner(phase2_database_url)


@pytest.mark.parametrize("database_timezone", ["UTC", "America/New_York"])
def test_challenge_expiry_after_lock_wait(
    phase2_database_url: str, monkeypatch: pytest.MonkeyPatch, database_timezone: str
) -> None:
    # Canonical ticket times must be UTC even when the DB session uses local time.
    monkeypatch.setenv(
        "PGOPTIONS", f"{os.environ.get('PGOPTIONS', '')} -c TimeZone={database_timezone}".strip()
    )
    _challenge_expiry_after_required_lock_wait_is_denied(phase2_database_url)


def test_owner_credential_expiry_after_lock_wait(phase2_database_url: str) -> None:
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment(phase2_database_url)


def test_fresh_time_after_each_required_wait(phase2_database_url: str) -> None:
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment(
        phase2_database_url, further_wait=True
    )
