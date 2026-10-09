from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Never
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from researchbase.api.app import create_app
from researchbase.application.literature_search_plan import LiteratureSearchPlanService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class Services:
    calls = 0

    @property
    def literature_search_plans(self):
        return self

    def create(self, command):
        self.calls += 1
        return {}


@pytest.mark.parametrize("method", ["post", "put"])
@pytest.mark.parametrize("languages", [["en", " en "], ["   "]])
def test_malformed_http_material_is_typed_422(languages, method):
    services = Services()
    with patch("researchbase.api.routes._verified_principal", return_value=object()):
        client = TestClient(create_app(services), raise_server_exceptions=False)
        path = f"/v1/projects/{uuid4()}/literature/search-plans"
        if method == "put":
            path += f"/{uuid4()}/versions/{uuid4()}"
        response = client.request(
            method,
            path,
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "objective": "Find evidence",
                "source_scope": "BIBLIOGRAPHIC",
                "language_scope": languages,
                "search_strategy": "KEYWORD",
                "planned_providers": ["provider-a"],
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert services.calls == 0


@pytest.mark.parametrize("current,allowed", [("VIEWER", False), ("RESEARCHER", True)])
def test_effective_role_controls_authorization(current, allowed):
    at = datetime.now(UTC)
    common = dict(
        actor_type="HUMAN",
        retired_at=None,
        membership_status="ACTIVE",
        effective_from=at - timedelta(days=2),
        binding_status="ACTIVE",
        bound_at=at - timedelta(days=3),
        revoked_at=None,
    )
    historical = {**common, "role": "OWNER", "effective_until": at - timedelta(days=1)}
    active = {**common, "role": current, "effective_until": None}
    repo = SimpleNamespace(authorize=lambda *_: [historical, active], at=lambda: at)
    service = LiteratureSearchPlanService(lambda: None, SimpleNamespace(is_valid=lambda *_: True))
    principal = SimpleNamespace(verified_at=at - timedelta(seconds=1))
    if allowed:
        assert service._authorize(repo, principal, uuid4())[0] == active
    else:
        with pytest.raises(ResearchBaseError) as error:
            service._authorize(repo, principal, uuid4())
        assert error.value.code is ErrorCode.FORBIDDEN


def test_replacement_uses_contract_15_reference_order():
    from uuid import UUID

    from researchbase.domain.literature_search_plan import FrozenResearchQuestionReference

    refs = (
        FrozenResearchQuestionReference(UUID(int=1), UUID(int=9), "a" * 64),
        FrozenResearchQuestionReference(UUID(int=2), UUID(int=3), "b" * 64),
    )
    rows = {
        r.version_id: {
            "research_question_id": r.research_question_id,
            "version_id": r.version_id,
            "content_hash": r.content_hash,
        }
        for r in refs
    }
    repo = SimpleNamespace(question=lambda version, **_: rows[version])
    service = LiteratureSearchPlanService(lambda: None, None)
    with patch("researchbase.application.literature_search_plan._validate_question_row"):
        result = service._resolve_refs(repo, uuid4(), refs)
    assert [r["version_id"] for r in result] == [UUID(int=3), UUID(int=9)]
    with patch("researchbase.application.literature_search_plan._validate_question_row"):
        copied = service._resolve_rows(repo, uuid4(), list(rows.values()))
    assert [r["version_id"] for r in copied] == [UUID(int=3), UUID(int=9)]


def test_literal_contract_15_golden_vectors():
    import json
    from pathlib import Path

    from tests.unit.phase2.test_literature_search_plan import material

    from researchbase.foundation.canonical_json import canonical_json_bytes

    vectors = json.loads(Path(__file__).with_name("search_plan_golden_vectors.json").read_text())
    for vector in vectors:
        languages = tuple(vector["languages"])
        value = material(languages)
        assert canonical_json_bytes(value.payload()).decode() == vector["canonical_utf8"]
        assert value.digest() == vector["sha256"]
        if languages:
            assert material((" e\u0301 ", " en ", "EN")).digest() == vector["sha256"]


def test_internal_application_failure_remains_500():
    services = Services()
    with (
        patch("researchbase.api.routes._verified_principal", return_value=object()),
        patch.object(services, "create", side_effect=RuntimeError("internal bug")),
    ):
        response = TestClient(create_app(services), raise_server_exceptions=False).post(
            f"/v1/projects/{uuid4()}/literature/search-plans",
            headers={"Idempotency-Key": str(uuid4())},
            json={
                "objective": "Valid objective",
                "source_scope": "BIBLIOGRAPHIC",
                "language_scope": [],
                "search_strategy": "KEYWORD",
                "planned_providers": [],
            },
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_verification_matrix_has_precise_existing_nodes_and_pending_results():
    import ast
    import json
    from pathlib import Path

    root = Path(__file__).parents[3]
    matrix = json.loads((root / "execution/phase2/PR2-03_Verification_Matrix.json").read_text())
    required = {
        "lifecycle",
        "RQ cardinality",
        "language NULL / []",
        "normalization",
        "golden hash vectors",
        "ordinals",
        "freeze immutability",
        "current pointer",
        "supersession",
        "effective authority",
        "authority loss",
        "per-command receipt",
        "rollback semantics",
        "idempotency",
        "addition races",
        "freeze races",
        "identity uniqueness",
        "DB direct-write guards",
        "HTTP malformed material",
        "CLI mapping",
        "migration",
        "schema checks",
        "FK indexes",
        "PR2-00 temporal",
        "Phase1 non-drift",
    }
    assert required <= {row["requirement"] for row in matrix["rows"]}
    rows = {row["requirement"]: row for row in matrix["rows"]}
    command_node = (
        "tests/integration/phase2/test_pr2_03_command_matrix.py::"
        "test_each_write_receipt_and_protected_effect_matrix"
    )
    assert rows["authority loss"]["tests"] == [
        f"{command_node}[authority_loss-{command}]"
        for command in [
            "create",
            "update",
            "add_question",
            "remove_question",
            "freeze",
            "revise",
            "abandon",
        ]
    ]
    assert rows["rollback semantics"]["tests"] == [
        f"{command_node}[rollback-{command}]"
        for command in [
            "create",
            "update",
            "add_question",
            "remove_question",
            "freeze",
            "revise",
            "abandon",
        ]
    ]
    for row in matrix["rows"]:
        assert row["result"] == "PENDING", (
            "execution results belong in host evidence, not the specification"
        )
        assert row["host_check"] and row["evidence_artifact"] and row["source_invariant"]
        for node in row["tests"]:
            file, case_name = node.split("::")
            name = case_name.split("[", 1)[0]
            functions = {
                item.name
                for item in ast.walk(ast.parse((root / file).read_text()))
                if isinstance(item, ast.FunctionDef)
            }
            assert name in functions, node
