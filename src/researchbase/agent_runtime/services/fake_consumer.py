"""Deterministic in-process accounting consumer. No external operation is performed."""

from researchbase.agent_runtime.application.task_safety import TaskSafetyService
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability


class TrustedFakeConsumer:
    def __init__(self, factory, credentials, artifact_store=None):
        self._capability = FakeConsumerCapability()
        self.service = TaskSafetyService(
            factory, credentials, artifact_store, consumer_capability=self._capability
        )

    def execute(self, principal, command):
        return self.service.execute(principal, command, consumer_capability=self._capability)

    def reconstruct(self, principal, project_id, task_id):
        return self.service.get_task_safety(principal, project_id, task_id)
