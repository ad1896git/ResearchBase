from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.foundation.ids import ActorId


def test_actor_rejects_blank_display_name() -> None:
    with pytest.raises(ValueError, match="display_name"):
        Actor(
            id=ActorId(uuid4()),
            actor_type=ActorType.HUMAN,
            display_name="   ",
            created_at=datetime.now(UTC),
        )


def test_project_and_workspace_preserve_typed_identity_and_defaults() -> None:
    actor_id = ActorId(uuid4())
    project_id = ProjectId(uuid4())
    workspace_id = WorkspaceId(uuid4())
    created_at = datetime(2026, 8, 27, 0, 0, tzinfo=UTC)

    project = Project(
        id=project_id,
        name="Project A",
        created_by=actor_id,
        created_at=created_at,
    )
    workspace = Workspace(
        id=workspace_id,
        project_id=project_id,
        name="Workspace A",
        created_by=actor_id,
        created_at=created_at,
    )

    assert project.lifecycle_status is LifecycleStatus.ACTIVE
    assert workspace.lifecycle_status is LifecycleStatus.ACTIVE
    assert project.row_version == 1
    assert workspace.row_version == 1
    assert workspace.project_id == project.id


@pytest.mark.parametrize("value", ["", "  "])
def test_project_and_workspace_reject_blank_names(value: str) -> None:
    actor_id = ActorId(uuid4())
    created_at = datetime.now(UTC)

    with pytest.raises(ValueError, match="name"):
        Project(id=ProjectId(uuid4()), name=value, created_by=actor_id, created_at=created_at)
    with pytest.raises(ValueError, match="name"):
        Workspace(
            id=WorkspaceId(uuid4()),
            project_id=ProjectId(uuid4()),
            name=value,
            created_by=actor_id,
            created_at=created_at,
        )


def test_actor_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Actor(
            id=ActorId(uuid4()),
            actor_type=ActorType.SERVICE,
            display_name="Service",
            created_at=datetime(2026, 8, 27),
        )
