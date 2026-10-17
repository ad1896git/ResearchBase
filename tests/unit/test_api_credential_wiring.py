"""The HTTP composition uses the CLI credential source at every Phase 2 boundary."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from researchbase.api.app import build_services, create_app
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.local_identity import LocalIdentityAdapter


@pytest.fixture
def composed(monkeypatch, tmp_path):
    import researchbase.api.app as composition

    at = datetime.now(UTC)
    principal = VerifiedPrincipal(uuid4(), "test", "OS_UID", "501", "test", at)
    project, source, proposal = uuid4(), uuid4(), uuid4()
    uow = MagicMock()
    uow.__enter__.return_value = uow
    for repo in (
        uow.source_identity,
        uow.source_version,
        uow.source_merge,
        uow.literature_search_plan,
        uow.novelty,
    ):
        repo.at.return_value = at
        repo.database_time.return_value = at
        repo.authorize.return_value = {}
    uow.source_merge.proposal.return_value = {
        "source_a_id": source,
        "source_b_id": uuid4(),
        "proposed_in_project_id": project,
    }
    uow.source_merge.project_ids_for_proposal.return_value = [project]
    monkeypatch.setattr(composition, "SqlAlchemyUnitOfWork", lambda factory: uow)
    monkeypatch.setattr(
        composition, "literature_search_execution_uow_factory", lambda factory: lambda: uow
    )
    root = tmp_path / "unconfigured-identity"
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(root))
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(tmp_path / "artifacts"))
    services = build_services()
    assert services.novelty is not None
    verifier = services.novelty._credentials
    assert isinstance(verifier, LocalIdentityAdapter)
    assert verifier.root == root
    assert not verifier.is_valid(principal, at)
    for service in (
        services.literature,
        services.source_versions,
        services.source_merge,
        services.source_merge_execution,
        services.literature_search_plans,
        services.literature_search_executions,
    ):
        assert service is not None
        assert service._credential_verifier is verifier
    assert services.novelty._literature._credentials is verifier
    assert services.decisions is not None
    assert services.decisions._credentials is verifier
    assert services.decisions._conclusions._literature._credentials is verifier
    check = Mock(wraps=verifier.is_valid)
    monkeypatch.setattr(verifier, "is_valid", check)
    app = create_app(services)

    @app.middleware("http")
    async def inject_principal(request, call_next):
        request.state.verified_principal = principal
        return await call_next(request)

    return app, principal, project, source, proposal, check, uow


@pytest.mark.parametrize(
    "service,code,status",
    [
        ("literature", "AUTHENTICATION_REQUIRED", 401),
        ("source_versions", "FORBIDDEN", 403),
        ("source_merge", "SOURCE_MERGE_APPROVAL_FORBIDDEN", 403),
        ("source_merge_execution", "SOURCE_MERGE_APPROVAL_FORBIDDEN", 403),
        ("literature_search_plans", "FORBIDDEN", 403),
        ("literature_search_executions", "FORBIDDEN", 403),
        ("novelty", "FORBIDDEN", 403),
    ],
)
def test_composed_http_services_deny_unconfigured_credentials(composed, service, code, status):
    app, principal, project, source, proposal, check, uow = composed
    base = f"/v1/projects/{project}"
    paths = {
        "literature": f"{base}/literature/sources/{source}",
        "source_versions": f"{base}/literature/sources/{source}/versions",
        "source_merge": f"{base}/literature/source-merge-proposals/{proposal}",
        "source_merge_execution": f"{base}/literature/source-merge-proposals/{proposal}:consume",
        "literature_search_plans": f"{base}/literature/search-plans",
        "literature_search_executions": f"/v1/literature/search-executions?project_id={project}",
        "novelty": f"{base}/search-coverage/{uuid4()}",
    }
    with TestClient(app) as client:
        if service == "source_merge_execution":
            response = client.post(
                paths[service],
                headers={"Idempotency-Key": str(uuid4())},
                json={
                    "proposal_basis_hash": "a" * 64,
                    "identity_basis_artifact": {"id": str(uuid4()), "content_hash": "b" * 64},
                },
            )
        else:
            response = client.get(paths[service])
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    check.assert_called_once()
    assert check.call_args.args[0] == principal
    uow.commit.assert_not_called()


def test_api_composed_nested_evidence_service_denies_unconfigured_credentials(composed):
    app, principal, project, source, _, check, uow = composed
    # Evidence has no standalone HTTP route; it is nested in the API NoveltyService.
    with pytest.raises(ResearchBaseError) as caught:
        app.state.services.novelty._literature.get(principal, project, uuid4())
    assert caught.value.code == ErrorCode.FORBIDDEN
    check.assert_called_once()
    uow.commit.assert_not_called()
