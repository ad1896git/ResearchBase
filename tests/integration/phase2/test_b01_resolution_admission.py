"""Exact bibliographic admission on real PostgreSQL, independently of M2 resolution."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.search_result_resolution import ExactResolutionQuery
from researchbase.application.source_identity import RejectSourceIdentifier
from researchbase.cli.composition import build_services
from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b01_support import count, create_version, record

pytest_plugins = ("tests.integration.phase2.b01_support",)


def test_explicit_admission_and_durable_restart(b01_env):
    e = b01_env
    tables = ("search_result_records", "metadata_observations", "literature_evidence")
    before = [count(e, t) for t in tables]
    value = record(e)
    assert value.source_version_id == e["command"].source_version_id
    fresh = build_services().search_result_resolutions
    assert fresh is not None
    assert (
        fresh.get_search_result_resolution(
            e["principal"], ExactResolutionQuery(e["project"], value.id)
        )
        == value
    )
    assert [count(e, t) for t in tables] == before
    assert count(e) == 1


def test_superseded_exact_version_does_not_follow_current(b01_env):
    e = b01_env
    other = create_version(
        e["bundle"], e["principal"], e["project"], replace(e["material"], abstract="New metadata")
    )
    assert other != e["command"].source_version_id
    assert record(e).source_version_id == e["command"].source_version_id


@pytest.mark.parametrize(
    "case,code",
    [
        ("no_doi", ErrorCode.IDENTIFIER_INVALID),
        ("title", ErrorCode.SOURCE_IDENTITY_CONFLICT),
        ("unverified", ErrorCode.SOURCE_IDENTITY_CONFLICT),
        ("rejected", ErrorCode.SOURCE_IDENTITY_CONFLICT),
        ("missing_source", ErrorCode.SOURCE_NOT_FOUND),
        ("wrong_version", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("missing_version", ErrorCode.SOURCE_VERSION_NOT_FOUND),
        ("draft", ErrorCode.FROZEN_REFERENCE_REQUIRED),
        ("missing_result", ErrorCode.NOT_FOUND),
        ("corrupt_basis", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("inaccessible_basis", ErrorCode.FORBIDDEN),
    ],
)
def test_admission_denies_without_append(b01_env, monkeypatch, case, code):
    e = b01_env
    changes = {}
    if case == "no_doi":
        # Keep title compatibility so DOI policy is the failure under test.
        version = create_version(
            e["bundle"], e["principal"], e["project"], replace(e["material"], title="No DOI")
        )
        changes = dict(search_result_record_id=e["results"][1], source_version_id=version)
    elif case == "title":
        changes["source_version_id"] = create_version(
            e["bundle"], e["principal"], e["project"], replace(e["material"], title="Different")
        )
    elif case == "unverified":
        from researchbase.persistence.search_result_resolution_repository import (
            SqlAlchemySearchResultResolutionRepository,
        )

        monkeypatch.setattr(
            SqlAlchemySearchResultResolutionRepository, "identifiers", lambda *_: []
        )
    elif case == "rejected":
        e["bundle"].literature.reject_source_identifier(
            RejectSourceIdentifier(
                e["principal"],
                e["project"],
                e["identifier"],
                e["basis"],
                "Rejected metadata",
                uuid4(),
            )
        )
    elif case == "missing_source":
        changes["source_id"] = uuid4()
    elif case == "missing_version":
        changes["source_version_id"] = uuid4()
    elif case == "missing_result":
        changes["search_result_record_id"] = uuid4()
    elif case == "draft":
        changes["source_version_id"] = create_version(
            e["bundle"],
            e["principal"],
            e["project"],
            replace(e["material"], abstract="Draft"),
            freeze=False,
        )
    elif case == "wrong_version":
        from uuid import UUID

        from researchbase.application.source_identity import RegisterLiteratureSource
        from researchbase.domain.source_identity import SourceKind

        source = e["bundle"].literature.register_literature_source(
            RegisterLiteratureSource(
                e["principal"], e["project"], SourceKind.PAPER, "Another", uuid4()
            )
        )
        changes["source_version_id"] = create_version(
            e["bundle"],
            e["principal"],
            e["project"],
            replace(e["material"], literature_source_id=UUID(str(source["source_id"]))),
        )
    elif case == "corrupt_basis":
        monkeypatch.setattr(e["service"]._store, "open", lambda _: b"altered")
    elif case == "inaccessible_basis":
        from researchbase.persistence.search_result_resolution_repository import (
            SqlAlchemySearchResultResolutionRepository,
        )

        original = SqlAlchemySearchResultResolutionRepository.artifact
        monkeypatch.setattr(
            SqlAlchemySearchResultResolutionRepository,
            "artifact",
            lambda repo, identity: dict(original(repo, identity) or {}, project_id=uuid4()),
        )
    with pytest.raises(ResearchBaseError) as error:
        record(e, **changes)
    assert error.value.code is code
    assert count(e) == 0


@pytest.mark.parametrize("kind", [SourceVersionKind.CORRECTED, SourceVersionKind.RETRACTED])
def test_current_correction_or_retraction_denies_new_admission(b01_env, kind):
    e = b01_env
    with e["engine"].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM source_versions WHERE id=:id"),
            {"id": e["command"].source_version_id},
        ).scalar_one()
        basis_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": e["basis"]}
        ).scalar_one()
    material = replace(
        e["material"],
        version_kind=kind,
        predecessor_source_version=FrozenSourceReference(e["command"].source_version_id, digest),
        correction_basis_artifact=FrozenSourceReference(e["basis"], basis_hash),
    )
    create_version(e["bundle"], e["principal"], e["project"], material)
    with pytest.raises(ResearchBaseError) as error:
        record(e)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert count(e) == 0


@pytest.mark.parametrize("active", [False, True])
def test_real_partial_result_requires_terminal_execution(b01_env, active):
    from datetime import UTC, datetime
    from uuid import UUID

    from researchbase.application.literature_search_execution import (
        CreateLiteratureSearchExecution,
        ExecuteLiteratureSearchExecution,
        LiteratureSearchExecutionService,
        SearchQueryInput,
    )
    from researchbase.application.literature_search_provider import (
        FakeSearchCapability,
        ProviderError,
        ProviderFailureKind,
        StaticSearchCapabilityRegistry,
    )
    from researchbase.domain.literature_search_execution import (
        DeliveryCertainty,
        SearchHit,
        SearchResponse,
    )

    e = b01_env
    healthy = e["bundle"].literature_search_executions
    with e["engine"].connect() as conn:
        plan = conn.execute(
            text("SELECT search_plan_version_id FROM literature_search_executions LIMIT 1")
        ).scalar_one()

    class FailingProvider(FakeSearchCapability):
        def search(self, request, context=None):
            if self.calls:
                raise ProviderError(
                    ProviderFailureKind.PERMANENT,
                    "PROVIDER_PERMANENT",
                    delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                )
            return super().search(request, context)

    provider = FailingProvider(
        "openalex",
        "works-v1",
        responses=[
            SearchResponse.success(
                provider_id="openalex",
                provider_version="works-v1",
                normalized_query="first",
                provider_request_id=None,
                hits=(
                    SearchHit("partial", "CRISPR Cas9", "https://doi.org/10.1234/abc", None, None),
                ),
                retrieved_at=datetime.now(UTC),
            ),
        ],
    )

    class ProcessStopped(BaseException):
        pass

    class Interrupted(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            super()._persist_outcome(*args, **kwargs)
            raise ProcessStopped()

    service = (Interrupted if active else LiteratureSearchExecutionService)(
        healthy._uow_factory,
        StaticSearchCapabilityRegistry((provider,)),
        credential_verifier=healthy._credential_verifier,
    )
    principal = e["principal"]
    created = service.create(
        CreateLiteratureSearchExecution(
            e["project"],
            plan,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "openalex",
            "works-v1",
            (SearchQueryInput("first"), SearchQueryInput("second")),
            principal=principal,
        )
    )
    execution = UUID(created["execution_id"])
    command = ExecuteLiteratureSearchExecution(
        execution,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=e["project"],
        principal=principal,
    )
    if active:
        with pytest.raises(ProcessStopped):
            service.execute(command)
    else:
        service.execute(command)
    history = healthy.get_provenance(principal, e["project"], execution)
    assert history["execution"]["status"] == ("RUNNING" if active else "FAILED")
    assert len(history["results"]) == 1
    result = UUID(history["results"][0]["id"])
    if active:
        with pytest.raises(ResearchBaseError) as error:
            record(e, search_result_record_id=result)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
        assert count(e) == 0
    else:
        assert record(e, search_result_record_id=result).search_result_record_id == result
