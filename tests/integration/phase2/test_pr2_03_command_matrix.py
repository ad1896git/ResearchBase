"""Each protected write: saved result, conflict, concurrent replay and rollback."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    RemoveLiteratureSearchPlanQuestion,
    ReviseLiteratureSearchPlan,
    TransitionLiteratureSearchPlanVersion,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _material,
    _question,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_idempotency import _create_material
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

COMMANDS = ["create", "update", "add_question", "remove_question", "freeze", "revise", "abandon"]
TABLES = [
    "literature_search_plans",
    "literature_search_plan_versions",
    "search_plan_question_inputs",
    "literature_search_plan_command_receipts",
]


def _snapshot(engine):
    with engine.connect() as c:
        return {
            table: c.execute(
                text(
                    f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {table} t"  # noqa: E501
                )
            ).scalar_one()
            for table in TABLES
        }


def _prepare(url, name):
    engine, service, principal, project, plan, version = _setup(url)
    q, qv, _ = _question(engine, project, principal.actor_id)
    if name in {"remove_question", "freeze"}:
        service.add_question(
            EditLiteratureSearchPlanQuestions(principal, project, plan, version, qv, uuid4())
        )
    if name == "revise":
        _freeze(engine, service, principal, project, plan, version)
    request = uuid4()
    if name == "create":
        command = CreateLiteratureSearchPlan(principal, project, _create_material(), request)
        changed = replace(command, material=_create_material("different objective"))
    else:
        if name == "update":
            command = UpdateLiteratureSearchPlanDraft(
                principal, project, plan, version, _material(plan, language_scope=("fr",)), request
            )
        elif name == "add_question":
            command = EditLiteratureSearchPlanQuestions(
                principal, project, plan, version, qv, request
            )
        elif name == "remove_question":
            command = RemoveLiteratureSearchPlanQuestion(
                principal, project, plan, version, q, request
            )
        elif name == "revise":
            command = ReviseLiteratureSearchPlan(principal, project, plan, version, request)
        else:
            command = TransitionLiteratureSearchPlanVersion(
                principal, project, plan, version, request
            )
        # A real same-plan row ensures changed-request rejection is a receipt
        # conflict rather than a missing-row short circuit.
        other = uuid4()
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO literature_search_plan_versions SELECT :new,plan_id,99,'DRAFT',objective,source_scope,inclusion_criteria,exclusion_criteria,time_range,language_scope,search_strategy,planned_providers,stopping_rule,NULL,hash_scheme,NULL,created_by,created_at,1 FROM literature_search_plan_versions WHERE id=:old"  # noqa: E501
                ),
                {"new": other, "old": version},
            )
        if name == "revise":
            # Revise requires no other draft for its first effect.
            with engine.begin() as c:
                c.execute(
                    text(
                        "UPDATE literature_search_plan_versions SET status='ABANDONED' WHERE id=:id"
                    ),
                    {"id": other},
                )
        changed = replace(
            command, **{("base_version_id" if name == "revise" else "version_id"): other}
        )
    return engine, service, command, changed


@pytest.mark.parametrize("name", COMMANDS)
@pytest.mark.parametrize("mode", ["replay_conflict", "rollback", "concurrent", "denied"])
def test_each_write_receipt_and_protected_effect_matrix(
    phase2_database_url, name, mode, record_property
):
    engine, service, command, changed = _prepare(phase2_database_url, name)
    before = _snapshot(engine)
    operation = getattr(service, name)
    if mode == "rollback":
        original = SqlAlchemyLiteratureSearchPlanRepository.insert_receipt

        def fail_after_receipt(repo, values):
            original(repo, values)
            raise RuntimeError("review rollback injection after effect and receipt")

        with patch.object(
            SqlAlchemyLiteratureSearchPlanRepository, "insert_receipt", fail_after_receipt
        ):
            with pytest.raises(RuntimeError, match="rollback injection"):
                operation(command)
        assert _snapshot(engine) == before
    elif mode == "denied":
        with patch.object(service._credential_verifier, "is_valid", return_value=False):
            with pytest.raises(ResearchBaseError) as error:
                operation(command)
        assert error.value.code is ErrorCode.FORBIDDEN
        assert _snapshot(engine) == before
    else:
        if mode == "concurrent":
            barrier = Barrier(2)

            def worker():
                barrier.wait(timeout=10)
                return operation(command)

            with ThreadPoolExecutor(max_workers=2) as pool:
                a, b = pool.submit(worker), pool.submit(worker)
                result = a.result(timeout=20)
                assert result == b.result(timeout=20)
        else:
            result = operation(command)
        after = _snapshot(engine)
        assert after != before
        assert operation(command) == result
        assert _snapshot(engine) == after
        with pytest.raises(ResearchBaseError) as error:
            operation(changed)
        assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
        assert _snapshot(engine) == after
        with engine.connect() as c:
            receipts = (
                c.execute(
                    text(
                        "SELECT request_hash,result_dto FROM literature_search_plan_command_receipts WHERE request_id=:id"  # noqa: E501
                    ),
                    {"id": command.request_id},
                )
                .mappings()
                .all()
            )
        assert len(receipts) == 1
        assert receipts[0]["result_dto"] == result
        # Saved DTO disclosure must still require current entitlement.
        with patch.object(service._credential_verifier, "is_valid", return_value=False):
            with pytest.raises(ResearchBaseError) as denied:
                operation(command)
        assert denied.value.code is ErrorCode.FORBIDDEN
        assert _snapshot(engine) == after
        record_property(
            "receipt_matrix",
            json.dumps(
                {
                    "command": name,
                    "mode": mode,
                    "receipt_count": len(receipts),
                    "request_hash": receipts[0]["request_hash"],
                    "result": result,
                    "duplicate_effect": False,
                }
            ),
        )
    record_property("rollback_or_denial", f"command={name};mode={mode};durable_state_verified=True")
    engine.dispose()
