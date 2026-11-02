"""Deterministic in-memory candidate preview. No providers, commands, or writes."""

from hashlib import sha256

from researchbase.agent_runtime.application.context_contracts import CanonicalContext
from researchbase.capabilities.coding.fake_contracts import (
    CandidateSource,
    FakeCodingCandidateRequest,
    FakeCodingCandidateResult,
    FakeProducer,
    FakeTestObservation,
    candidate_patch,
    request_digest,
    validate_context,
    validate_result,
)


class FakeCodingPreviewAdapter:
    def preview(
        self, request: FakeCodingCandidateRequest, context: CanonicalContext
    ) -> FakeCodingCandidateResult:
        validate_context(request, context)
        patch = candidate_patch(request)
        result = FakeCodingCandidateResult(
            project_id=request.project_id,
            task_id=request.task_id,
            step_id=request.step_id,
            repository_artifact_ref=request.repository_artifact_ref,
            workspace_digest=request.workspace_digest,
            request_digest=request_digest(request),
            patch=patch,
            patch_sha256=sha256(patch).hexdigest(),
            source_candidates=tuple(
                CandidateSource(
                    path=f.path, bytes=f.proposed_bytes, sha256=sha256(f.proposed_bytes).hexdigest()
                )
                for f in request.fixture_files
            ),
            test_observation=FakeTestObservation(declared_commands=request.test_commands),
            producer=FakeProducer(),
        )
        validate_result(request, result)
        return result
