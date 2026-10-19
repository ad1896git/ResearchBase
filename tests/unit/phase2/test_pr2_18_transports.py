"""Closed HTTP schemas and exact status/CLI error mappings."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from researchbase.api.app import create_app
from researchbase.api.routes import NoveltyAssessmentIn, PriorArtIn, SearchCoverageIn
from researchbase.cli.errors import CLI_EXIT_CODES, INTERNAL_ERROR_EXIT_CODE
from researchbase.foundation.errors import ErrorCode


@pytest.mark.parametrize(
    "model,values",
    [
        (
            SearchCoverageIn,
            {
                "id": str(uuid4()),
                "search_plan_version_id": str(uuid4()),
                "search_execution_ids": [str(uuid4())],
                "coverage_limitations": "scope",
            },
        ),
        (
            PriorArtIn,
            {
                "id": str(uuid4()),
                "claim_version_id": str(uuid4()),
                "source_version_id": str(uuid4()),
                "relation": "RELATED",
                "rationale": "comparison",
                "literature_evidence_ids": [str(uuid4())],
            },
        ),
        (
            NoveltyAssessmentIn,
            {
                "id": str(uuid4()),
                "claim_version_id": str(uuid4()),
                "search_coverage_id": str(uuid4()),
                "assessment": "INCONCLUSIVE",
                "limitations": "limits",
            },
        ),
    ],
)
def test_closed_transport(model, values):
    assert model.model_validate(values)
    for extra in (
        "assessed_by",
        "created_by",
        "query_count",
        "material_version",
        "captured_results",
        "captured_unresolved_result_count",
    ):
        with pytest.raises(ValidationError):
            model.model_validate({**values, extra: str(uuid4())})
    with pytest.raises(ValidationError):
        model.model_validate({**values, "id": uuid4().hex})
    with pytest.raises(ValidationError):
        model.model_validate({**values, "id": True})


def test_only_exact_id_get_routes():
    schema = create_app().openapi()
    for name in ("search-coverage", "prior-art-relations", "novelty-assessments"):
        base = "/v1/projects/{project_id}/" + name
        assert set(schema["paths"][base]) == {"post"}
        assert set(schema["paths"][base + "/{id}"]) == {"get"}
        assert "200" in schema["paths"][base]["post"]["responses"]


@pytest.mark.parametrize(
    "code,exit_code",
    [
        (ErrorCode.AUTHENTICATION_REQUIRED, 3),
        (ErrorCode.FORBIDDEN, 3),
        (ErrorCode.VALIDATION_ERROR, 2),
        (ErrorCode.NOT_FOUND, 3),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 5),
        (ErrorCode.INVALID_STATE_TRANSITION, 4),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 5),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 4),
        (ErrorCode.IMMUTABLE_RECORD, 4),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 5),
        (ErrorCode.CONCURRENT_MODIFICATION, 4),
    ],
)
def test_cli_pinned_mappings(code, exit_code):
    assert CLI_EXIT_CODES[code] == exit_code
    assert INTERNAL_ERROR_EXIT_CODE == 1


@pytest.fixture(params=[1, 2])
def novelty_transports(request):
    version = request.param
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from typing import Any, cast
    from unittest.mock import Mock

    from fastapi.testclient import TestClient

    from researchbase.application.novelty import (
        CoverageQuality,
        CurrentValidity,
        NoveltyReadback,
        PriorArtReadback,
        SearchCoverageReadback,
    )
    from researchbase.cli.app import create_app as create_cli
    from researchbase.domain.novelty import HashRef, NoveltyOutcome, PriorArtKind
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    now = datetime.now(UTC)
    actor = uuid4()
    project = uuid4()
    request = uuid4()
    plan = uuid4()
    claim = uuid4()
    source = uuid4()
    evidence = uuid4()
    principal = VerifiedPrincipal(actor, "test-deployment", "OS_UID", "501", "credential", now)
    quality = CoverageQuality(now, None if version == 1 else 0, 0, True, False, (), (), ())
    valid = CurrentValidity(now, True, ())
    cov = SearchCoverageReadback(
        request,
        project,
        HashRef("LiteratureSearchPlanVersion", plan, "a" * 64),
        (uuid4(),),
        (),
        0,
        0,
        0,
        None,
        "Selected scope.",
        now,
        actor,
        "a" * 64,
        "sha256-cjson-v1",
        quality,
        version,
    )
    prior = PriorArtReadback(
        request,
        project,
        HashRef("ClaimVersion", claim, "a" * 64),
        HashRef("SourceVersion", source, "a" * 64),
        PriorArtKind.RELATED,
        "Comparison.",
        (HashRef("LiteratureEvidence", evidence, "a" * 64),),
        actor,
        now,
        actor,
        "b" * 64,
        "sha256-cjson-v1",
        valid,
    )
    novel = NoveltyReadback(
        request,
        project,
        prior.claim_version,
        cov,
        NoveltyOutcome.INCONCLUSIVE,
        "Limited.",
        None,
        actor,
        now,
        actor,
        "c" * 64,
        "sha256-cjson-v1",
        valid,
        None,
        None,
    )
    service = Mock()
    bodies = [
        {
            "id": str(request),
            "search_plan_version_id": str(plan),
            "search_execution_ids": [str(cov.search_execution_ids[0])],
            "coverage_limitations": "Selected scope.",
        },
        {
            "id": str(request),
            "claim_version_id": str(claim),
            "source_version_id": str(source),
            "relation": "RELATED",
            "rationale": "Comparison.",
            "literature_evidence_ids": [str(evidence)],
        },
        {
            "id": str(request),
            "claim_version_id": str(claim),
            "search_coverage_id": str(cov.id),
            "assessment": "INCONCLUSIVE",
            "limitations": "Limited.",
        },
    ]
    paths = ["search-coverage", "prior-art-relations", "novelty-assessments"]
    methods = ["search_coverage", "prior_art_relation", "novelty_assessment"]
    cli_names = ["search-coverage", "prior-art-relation", "novelty-assessment"]
    for method, value in zip(methods, [cov, prior, novel], strict=True):
        getattr(service, "record_" + method).return_value = value
        getattr(service, "read_" + method).return_value = value
    bundle = SimpleNamespace(
        application=object(),
        provenance=object(),
        governance=object(),
        governance_queries=object(),
        novelty=service,
        verified_principal=principal,
    )
    app = create_app(cast(Any, bundle))

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.verified_principal = principal
        return await call_next(request)

    yield SimpleNamespace(
        client=TestClient(app, raise_server_exceptions=False),
        cli=create_cli(cast(Any, bundle)),
        service=service,
        principal=principal,
        project=project,
        id=request,
        bodies=bodies,
        paths=paths,
        methods=methods,
        cli_names=cli_names,
    )


def test_all_six_http_and_cli_commands_share_principal(novelty_transports):
    import json

    from typer.testing import CliRunner

    e = novelty_transports
    for body, path, method, cli_name in zip(e.bodies, e.paths, e.methods, e.cli_names, strict=True):
        base = f"/v1/projects/{e.project}/{path}"
        assert e.client.post(base, json=body).status_code == 200
        assert e.client.post(base, json=body).status_code == 200
        response = e.client.get(base + "/" + str(e.id))
        assert response.status_code == 200
        if method in {"search_coverage", "novelty_assessment"}:
            coverage = response.json()
            if method == "novelty_assessment":
                coverage = coverage["search_coverage"]
            version = coverage["material_version"]
            assert coverage["quality"]["captured_unresolved_result_count"] == (
                None if version == 1 else 0
            )
        for action in ("record", "read"):
            args = ["literature", action + "-" + cli_name, "--project-id", str(e.project), "--json"]
            args += (
                ["--material-json", json.dumps(body)] if action == "record" else ["--id", str(e.id)]
            )
            result = CliRunner().invoke(e.cli, args)
            assert result.exit_code == 0, (result.stdout, result.stderr, result.exception)
            if method in {"search_coverage", "novelty_assessment"}:
                coverage = json.loads(result.stdout)
                if method == "novelty_assessment":
                    coverage = coverage["search_coverage"]
                version = coverage["material_version"]
                assert coverage["quality"]["captured_unresolved_result_count"] == (
                    None if version == 1 else 0
                )
            assert getattr(e.service, action + "_" + method).call_args.args[0] is e.principal


@pytest.mark.parametrize(
    "code,http_status,exit_code",
    [
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
        (ErrorCode.IMMUTABLE_RECORD, 409, 4),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 409, 5),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
    ],
)
def test_http_cli_error_envelopes(novelty_transports, code, http_status, exit_code):
    import json

    from typer.testing import CliRunner

    from researchbase.foundation.errors import ResearchBaseError

    e = novelty_transports
    e.service.record_search_coverage.side_effect = ResearchBaseError(code, "bounded diagnostic")
    response = e.client.post(f"/v1/projects/{e.project}/search-coverage", json=e.bodies[0])
    assert response.status_code == http_status
    assert response.json()["error"]["code"] == code.value
    result = CliRunner().invoke(
        e.cli,
        [
            "literature",
            "record-search-coverage",
            "--project-id",
            str(e.project),
            "--material-json",
            json.dumps(e.bodies[0]),
            "--json",
        ],
    )
    assert result.exit_code == exit_code
    assert json.loads(result.stderr)["error"]["code"] == code.value


def test_unexpected_failures_are_sanitized(novelty_transports):
    import json

    from typer.testing import CliRunner

    e = novelty_transports
    e.service.record_search_coverage.side_effect = RuntimeError(
        "secret-driver-and-credential-details"
    )
    response = e.client.post(f"/v1/projects/{e.project}/search-coverage", json=e.bodies[0])
    assert response.status_code == 500
    assert "secret-driver" not in response.text
    result = CliRunner().invoke(
        e.cli,
        [
            "literature",
            "record-search-coverage",
            "--project-id",
            str(e.project),
            "--material-json",
            json.dumps(e.bodies[0]),
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert json.loads(result.stderr)["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-driver" not in result.stderr
