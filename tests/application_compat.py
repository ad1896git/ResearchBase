"""Legacy read-model facade for historical direct-Application tests.

Production ApplicationService writes are intentionally canonical WriteResult
commands.  These tests exercise older direct-call assertions through the
same Application-owned projection used by the real adapters.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from researchbase.application.commands import (
    _WRITE_PROJECTION_TARGETS,
    ApplicationService,
    UowFactory,
)
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.time import Clock


class LegacyApplicationService(ApplicationService):
    def __getattribute__(self, name: str) -> Any:
        target = _WRITE_PROJECTION_TARGETS.get(name)
        if target is None:
            return super().__getattribute__(name)
        method = super().__getattribute__(name)

        def legacy_method(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            return super(LegacyApplicationService, self).project_write_result(result, target)

        return legacy_method


def legacy_application_factory(
    uow_factory: UowFactory,
    clock: Clock,
    artifact_store: ArtifactStore | None = None,
) -> Callable[[], LegacyApplicationService]:
    return lambda: LegacyApplicationService(uow_factory, clock, artifact_store)
