from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from researchbase.domain.phase2_identity import VerifiedPrincipal, effective_owner


class CredentialVerifier:
    def __init__(self, valid_until: datetime) -> None:
        self.valid_until = valid_until
        self.checked_at: datetime | None = None

    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
        self.checked_at = at
        return at < self.valid_until


def test_owner_role_does_not_outlive_verified_credential() -> None:
    expiry = datetime(2026, 10, 3, 12, tzinfo=UTC)
    checked_at = expiry + timedelta(microseconds=1)
    principal = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-a",
        subject_kind="MTLS_URI",
        subject_value="spiffe://example.org/operator/7",
        credential_id="cert-sha256:abcd",
        verified_at=expiry - timedelta(hours=1),
    )
    verifier = CredentialVerifier(expiry)

    assert effective_owner(
        role_valid=True,
        membership_valid=True,
        actor_retired=False,
        principal=principal,
        verifier=verifier,
        at=expiry - timedelta(microseconds=1),
    )
    assert not effective_owner(
        role_valid=True,
        membership_valid=True,
        actor_retired=False,
        principal=principal,
        verifier=verifier,
        at=checked_at,
    )
    assert verifier.checked_at == checked_at
