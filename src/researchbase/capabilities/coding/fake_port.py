"""Candidate-only preview protocol, deliberately separate from formal execute_task."""

from typing import Protocol

from researchbase.agent_runtime.application.context_contracts import CanonicalContext
from researchbase.capabilities.coding.fake_contracts import (
    FakeCodingCandidateRequest,
    FakeCodingCandidateResult,
)


class FakeCodingCandidatePort(Protocol):
    def preview(
        self, request: FakeCodingCandidateRequest, context: CanonicalContext
    ) -> FakeCodingCandidateResult: ...
