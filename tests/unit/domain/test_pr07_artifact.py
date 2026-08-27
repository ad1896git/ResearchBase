from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from tests.contracts.version_contract import VersionFixture, assert_version_contract

from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import RAW_BYTES_HASH_SCHEME, ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus

FIXED_TIME = datetime(2026, 8, 27, 8, 0, tzinfo=UTC)
ARTIFACT_ID = ArtifactId(UUID("11111111-1111-7111-8111-111111111111"))
VERSION_ID = ArtifactVersionId(UUID("22222222-2222-7222-8222-222222222222"))
OTHER_VERSION_ID = ArtifactVersionId(UUID("33333333-3333-7333-8333-333333333333"))
PROJECT_ID = ProjectId(UUID("44444444-4444-7444-8444-444444444444"))
ACTOR_ID = ActorId(UUID("55555555-5555-7555-8555-555555555555"))
HASH = ContentHash("a" * 64)


def version(**overrides: object) -> ArtifactVersion:
    values: dict[str, object] = {
        "id": VERSION_ID,
        "artifact_id": ARTIFACT_ID,
        "version_number": 1,
        "status": VersionStatus.DRAFT,
        "locator": "sha256:" + "a" * 64,
        "media_type": "text/plain",
        "byte_size": 7,
        "content_hash": HASH,
        "metadata": {"label": "initial"},
        "created_by": ACTOR_ID,
        "created_at": FIXED_TIME,
    }
    values.update(overrides)
    return ArtifactVersion(**values)  # type: ignore[arg-type]


def test_artifact_accepts_nullable_project_and_validates_identity() -> None:
    artifact = Artifact(
        id=ARTIFACT_ID,
        project_id=None,
        artifact_type="dataset-manifest",
        name="Manifest",
        description=None,
        created_by=ACTOR_ID,
        created_at=FIXED_TIME,
    )

    assert artifact.project_id is None
    assert artifact.current_version_id is None
    assert artifact.row_version == 1


@pytest.mark.parametrize("name", ["", "   "])
def test_artifact_rejects_blank_name(name: str) -> None:
    with pytest.raises(ValueError, match="name must not be blank"):
        Artifact(
            id=ARTIFACT_ID,
            project_id=PROJECT_ID,
            artifact_type="text",
            name=name,
            description=None,
            created_by=ACTOR_ID,
            created_at=FIXED_TIME,
        )


def test_artifact_version_freeze_preserves_exact_byte_hash() -> None:
    frozen = version().freeze(FixedClock(datetime(2026, 8, 27, 9, 0, tzinfo=UTC)))

    assert frozen.status is VersionStatus.FROZEN
    assert frozen.content_hash == HASH
    assert frozen.frozen_at == datetime(2026, 8, 27, 9, 0, tzinfo=UTC)


def test_artifact_version_draft_metadata_edit_is_allowed_but_frozen_edit_is_not() -> None:
    edited = version().edit_metadata(
        locator="file:///relocated",
        media_type="application/octet-stream",
        byte_size=7,
        metadata={"label": "edited"},
    )
    assert edited.content_hash == HASH
    assert edited.metadata == {"label": "edited"}

    with pytest.raises(ResearchBaseError) as raised:
        version().freeze(FixedClock(FIXED_TIME)).edit_metadata(
            locator="file:///forbidden",
            media_type="text/plain",
            byte_size=7,
            metadata={"label": "forbidden"},
        )
    assert raised.value.code is ErrorCode.IMMUTABLE_RECORD


def test_artifact_version_is_frozen_dataclass_without_role_or_hash_recalculation() -> None:
    current = version()
    assert not hasattr(current, "role")
    assert not hasattr(current, "input_role")
    with pytest.raises(FrozenInstanceError):
        current.locator = "file:///changed"  # type: ignore[misc]


class ArtifactVersionContractAdapter:
    """Adapt the real ArtifactVersion to the shared PR-03 lifecycle contract."""

    def __init__(self, material: object) -> None:
        self.version = version(metadata=material)
        self.non_material_metadata = {"id": UUID(int=1), "created_at": FIXED_TIME}

    @property
    def status(self) -> VersionStatus:
        return self.version.status

    @property
    def content_hash(self) -> ContentHash:
        return self.version.content_hash

    @property
    def hash_scheme(self) -> str:
        return RAW_BYTES_HASH_SCHEME

    @property
    def frozen_at(self) -> datetime | None:
        return self.version.frozen_at

    def edit_material(self, material: object) -> None:
        self.version = self.version.edit_metadata(
            locator=self.version.locator,
            media_type=self.version.media_type,
            byte_size=self.version.byte_size,
            metadata=material,
        )

    def freeze(self, clock: FixedClock) -> None:
        self.version = self.version.freeze(clock)

    def transition_to(self, target: VersionStatus) -> None:
        self.version = self.version.transition_to(target)


def test_artifact_version_runs_through_shared_pr03_contract() -> None:
    assert_version_contract(
        cast(Callable[[object], VersionFixture], ArtifactVersionContractAdapter),
        verify_material_hash=False,
    )
