from __future__ import annotations

from tests.integration.phase2.test_pr2_00_challenges import (
    _challenge_consumers_have_one_winner,
    _challenge_expiry_after_required_lock_wait_is_denied,
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment,
)


def test_challenge_single_winner(phase2_database_url: str) -> None:
    _challenge_consumers_have_one_winner(phase2_database_url)


def test_challenge_expiry_after_lock_wait(phase2_database_url: str) -> None:
    _challenge_expiry_after_required_lock_wait_is_denied(phase2_database_url)


def test_owner_credential_expiry_after_lock_wait(phase2_database_url: str) -> None:
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment(phase2_database_url)


def test_fresh_time_after_each_required_wait(phase2_database_url: str) -> None:
    _owner_credential_expiry_after_project_lock_wait_denies_role_assignment(
        phase2_database_url, further_wait=True
    )
