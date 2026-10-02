from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from researchbase.domain.evidence import Dataset, DatasetId, DatasetSnapshot, DatasetSnapshotId
from researchbase.domain.organization import LifecycleStatus, ProjectId
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId

FIXED_TIME = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)
DATASET_ID = DatasetId(UUID("11111111-1111-7111-8111-111111111111"))
SNAPSHOT_ID = DatasetSnapshotId(UUID("22222222-2222-7222-8222-222222222222"))
PROJECT_ID = ProjectId(UUID("33333333-3333-7333-8333-333333333333"))
ACTOR_ID = ActorId(UUID("44444444-4444-7444-8444-444444444444"))
MANIFEST_HASH = ContentHash("a" * 64)
SELECTION = {"split": "train", "where": {"status": "ready"}}


def test_dataset_accepts_nullable_project_and_validates_identity() -> None:
    dataset = Dataset(
        id=DATASET_ID,
        project_id=None,
        name="External dataset",
        description=None,
        source_locator="s3://bucket/data",
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by=ACTOR_ID,
        created_at=FIXED_TIME,
    )

    assert dataset.project_id is None
    assert dataset.row_version == 1


@pytest.mark.parametrize("name", ["", "   "])
def test_dataset_rejects_blank_name(name: str) -> None:
    with pytest.raises(ValueError, match="name must not be blank"):
        Dataset(
            id=DATASET_ID,
            project_id=PROJECT_ID,
            name=name,
            description=None,
            source_locator=None,
            created_by=ACTOR_ID,
            created_at=FIXED_TIME,
        )


def test_snapshot_material_hash_uses_manifest_and_selection_only() -> None:
    material = {"manifest_hash": str(MANIFEST_HASH), "selection_definition": SELECTION}
    snapshot = DatasetSnapshot(
        id=SNAPSHOT_ID,
        dataset_id=DATASET_ID,
        manifest_hash=MANIFEST_HASH,
        selection_definition=SELECTION,
        manifest_locator="file:///first/manifest.json",
        content_hash=sha256_canonical_json(material),
        created_by=ACTOR_ID,
        created_at=FIXED_TIME,
    )

    assert snapshot.material_payload() == material
    assert snapshot.content_hash == sha256_canonical_json(snapshot.material_payload())
    assert not hasattr(snapshot, "freeze")
    assert not hasattr(snapshot, "edit_material")


def test_snapshot_is_immutable() -> None:
    snapshot = DatasetSnapshot(
        id=SNAPSHOT_ID,
        dataset_id=DATASET_ID,
        manifest_hash=MANIFEST_HASH,
        selection_definition=SELECTION,
        manifest_locator=None,
        content_hash=sha256_canonical_json(
            {"manifest_hash": str(MANIFEST_HASH), "selection_definition": SELECTION}
        ),
        created_by=ACTOR_ID,
        created_at=FIXED_TIME,
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.manifest_locator = "file:///changed"  # type: ignore[misc]


def _snapshot_hash(snapshot: DatasetSnapshot) -> ContentHash:
    return sha256_canonical_json(snapshot.material_payload())


def _baseline_snapshot() -> DatasetSnapshot:
    return DatasetSnapshot(
        id=SNAPSHOT_ID,
        dataset_id=DATASET_ID,
        manifest_hash=MANIFEST_HASH,
        selection_definition=SELECTION,
        manifest_locator="file:///first/manifest.json",
        content_hash=sha256_canonical_json(
            {"manifest_hash": str(MANIFEST_HASH), "selection_definition": SELECTION}
        ),
        created_by=ACTOR_ID,
        created_at=FIXED_TIME,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", DatasetSnapshotId(UUID("55555555-5555-7555-8555-555555555555"))),
        ("dataset_id", DatasetId(UUID("66666666-6666-7666-8666-666666666666"))),
        ("manifest_locator", "file:///second/manifest.json"),
        ("created_by", ActorId(UUID("77777777-7777-7777-8777-777777777777"))),
        ("created_at", datetime(2026, 8, 27, 7, 0, tzinfo=UTC)),
    ],
)
def test_excluded_snapshot_fields_do_not_change_bare_content_hash(
    field: str, value: object
) -> None:
    baseline = _baseline_snapshot()
    variant = replace(baseline, **{field: value})

    assert _snapshot_hash(variant) == _snapshot_hash(baseline)


def test_each_material_snapshot_field_changes_bare_content_hash() -> None:
    baseline = _baseline_snapshot()
    changed_manifest = ContentHash("b" * 64)
    changed_selection = {"split": "test"}
    manifest_variant = replace(
        baseline,
        manifest_hash=changed_manifest,
        content_hash=sha256_canonical_json(
            {
                "manifest_hash": str(changed_manifest),
                "selection_definition": SELECTION,
            }
        ),
    )
    selection_variant = replace(
        baseline,
        selection_definition=changed_selection,
        content_hash=sha256_canonical_json(
            {
                "manifest_hash": str(MANIFEST_HASH),
                "selection_definition": changed_selection,
            }
        ),
    )

    assert _snapshot_hash(manifest_variant) != _snapshot_hash(baseline)
    assert _snapshot_hash(selection_variant) != _snapshot_hash(baseline)


def test_snapshot_material_hash_is_canonical_key_order_stable() -> None:
    first = {"manifest_hash": "a" * 64, "selection_definition": {"b": 2, "a": 1}}
    second = {"selection_definition": {"a": 1, "b": 2}, "manifest_hash": "a" * 64}

    assert sha256_canonical_json(first) == sha256_canonical_json(second)
