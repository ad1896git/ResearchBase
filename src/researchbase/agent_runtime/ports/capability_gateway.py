"""Caller-neutral gateway port; implementations own the bounded command sequence."""

from typing import Protocol

from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    CapabilityRequest,
    CapabilityResult,
)


class CapabilityGateway(Protocol):
    def invoke(
        self, request: CapabilityRequest, context: AgentExecutionContext
    ) -> CapabilityResult: ...
