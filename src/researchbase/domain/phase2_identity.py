"""Caller-neutral identity values and time-sensitive authorization rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from researchbase.foundation.time import to_utc


@dataclass(frozen=True, slots=True)
class VerifiedPrincipal:
    """A principal resolved by a trusted deployment authentication adapter."""

    actor_id: UUID
    deployment_id: str
    subject_kind: str
    subject_value: str
    credential_id: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, UUID):
            raise TypeError("actor_id must be a UUID")
        for field_name in (
            "deployment_id",
            "subject_kind",
            "subject_value",
            "credential_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if self.subject_kind not in {"OS_UID", "MTLS_URI"}:
            raise ValueError("subject_kind must be OS_UID or MTLS_URI")
        object.__setattr__(self, "verified_at", to_utc(self.verified_at))


class CredentialVerifier(Protocol):
    """Rechecks current validity using the trusted credential provider."""

    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


def effective_owner(
    *,
    role_valid: bool,
    membership_valid: bool,
    actor_retired: bool,
    principal: VerifiedPrincipal,
    verifier: CredentialVerifier,
    at: datetime,
) -> bool:
    """Evaluate OWNER authority using advancing time and live credential state."""

    checked_at = to_utc(at)
    if (
        not role_valid
        or not membership_valid
        or actor_retired
        or principal.verified_at > checked_at
    ):
        return False
    try:
        return bool(verifier.is_valid(principal, checked_at))
    except Exception:
        return False
