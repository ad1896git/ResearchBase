"""Historical material, entitlement, idempotency and uncertain-commit recovery."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    ExactStrategyQuery,
)
from researchbase.domain.research import HypothesisVersionId, ResearchQuestionVersionId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import SystemClock
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.b02_support import (
    capture,
    count,
    hcommand,
    qcommand,
    reader_role,
    restart,
)

pytest_plugins = ("tests.integration.phase2.b02_support", "tests.integration.phase2.b01_support")


@pytest.mark.parametrize("ending", ["freeze", "abandon", "supersede"])
@pytest.mark.parametrize("kind", ["question", "hypothesis"])
def test_replay_after_draft_edit_freeze_and_abandon(b02_env, kind, ending):
    e = b02_env
    saved = capture(e)
    cmd = qcommand(e, saved) if kind == "question" else hcommand(e, saved)
    invoke = getattr(e["service"], f"promote_strategy_{kind}")
    value = invoke(e["principal"], cmd)
    with e["factory"]() as uow:
        repo = uow.research_questions if kind == "question" else uow.hypotheses
        version = repo.get_version(
            ResearchQuestionVersionId(value.research_question_version_id)
            if kind == "question"
            else HypothesisVersionId(value.hypothesis_version_id)
        )
        if kind == "question":
            edited = version.edit_material(
                question_text="Edited question", scope=None, rationale="Later"
            )
        else:
            edited = version.edit_material(
                statement="Edited hypothesis",
                expected_direction=None,
                success_criteria=None,
                rationale="Later",
            )
        repo.update_version(edited, version.row_version)
        uow.commit()
    assert invoke(e["principal"], cmd) == value
    with e["factory"]() as uow:
        repo = uow.research_questions if kind == "question" else uow.hypotheses
        version = repo.get_version(
            ResearchQuestionVersionId(value.research_question_version_id)
            if kind == "question"
            else HypothesisVersionId(value.hypothesis_version_id)
        )
        from researchbase.foundation.versioning import VersionStatus

        terminal = (
            version.transition_to(VersionStatus.ABANDONED)
            if ending == "abandon"
            else version.freeze(SystemClock())
        )
        repo.update_version(terminal, version.row_version)
        if ending == "supersede":
            current = repo.get_version(version.id)
            repo.update_version(
                current.transition_to(VersionStatus.SUPERSEDED), current.row_version
            )
        uow.commit()
    assert (
        getattr(restart(e), f"get_strategy_{kind}_promotion")(
            e["other"], ExactStrategyQuery(cmd.id, e["project"])
        )
        == value
    )
    assert invoke(e["principal"], cmd) == value


@pytest.mark.parametrize("kind", ["capture", "question", "hypothesis"])
def test_replay_material_actor_duplicate_and_credentials(b02_env, kind):
    e = b02_env
    if kind == "capture":
        cmd = CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
        invoke = e["service"].capture_native_strategy
        changes = {"topic": "Changed"}
    else:
        saved = capture(e)
        cmd = qcommand(e, saved) if kind == "question" else hcommand(e, saved)
        invoke = getattr(e["service"], f"promote_strategy_{kind}")
        changes = {"rationale": "Changed"}
    value = invoke(e["principal"], cmd)
    assert invoke(e["principal"], cmd) == value
    with pytest.raises(ResearchBaseError) as denied:
        invoke(e["other"], replace(cmd, **changes))
    assert denied.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as denied:
        invoke(e["principal"], replace(cmd, **changes))
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    if kind != "capture":
        with pytest.raises(ResearchBaseError) as denied:
            invoke(e["principal"], replace(cmd, id=uuid4()))
        assert denied.value.code is ErrorCode.DUPLICATE_CONTENT
    reader_role(e, e["principal"])
    assert invoke(e["principal"], cmd) == value
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError) as denied:
        invoke(e["principal"], cmd)
    assert denied.value.code is ErrorCode.FORBIDDEN


def test_lost_reader_denies_saved_replay(b02_env):
    e = b02_env
    saved = capture(e)
    cmd = qcommand(e, saved)
    e["service"].promote_strategy_question(e["principal"], cmd)
    reader_role(e, e["principal"], None)
    with pytest.raises(ResearchBaseError) as denied:
        e["service"].promote_strategy_question(e["principal"], cmd)
    assert denied.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize("kind", ["capture", "question", "hypothesis"])
def test_unknown_commit_response_recovers_exact_id(b02_env, monkeypatch, kind):
    e = b02_env
    saved = capture(e)
    cmd = (
        qcommand(e, saved)
        if kind == "question"
        else hcommand(e, saved)
        if kind == "hypothesis"
        else CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
    )
    invoke = (
        e["service"].capture_native_strategy
        if kind == "capture"
        else getattr(e["service"], f"promote_strategy_{kind}")
    )
    original = SqlAlchemyUnitOfWork.commit

    # Trigger only at persistence commit (capture preflight is read-only).
    with monkeypatch.context() as patch:

        def lost_write(uow):
            readonly = (
                uow._require_session()
                .connection()
                .get_execution_options()
                .get("postgresql_readonly")
            )
            original(uow)
            if uow._b02_error_normalization and not readonly:
                raise RuntimeError("lost commit reply")

        patch.setattr(SqlAlchemyUnitOfWork, "commit", lost_write)
        with pytest.raises(RuntimeError, match="lost commit reply"):
            invoke(e["principal"], cmd)
    recovered = invoke(e["principal"], cmd)
    assert recovered.id == cmd.id
    assert count(
        e,
        "strategy_question_admissions"
        if kind == "question"
        else "strategy_hypothesis_admissions"
        if kind == "hypothesis"
        else "strategy_candidate_captures",
    ) == (2 if kind == "capture" else 1)


@pytest.mark.parametrize("change", ["retract", "correct"])
def test_historical_replay_survives_source_usability_changes(b02_env, change):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind

    e = b02_env
    saved = capture(e)
    cmd = qcommand(e, saved)
    admitted = e["service"].promote_strategy_question(e["principal"], cmd)
    source = e["sources"][0]
    with e["factory"]() as uow:
        row = uow.source_version.version(source)
        material = _material_from_row(uow.source_version, row)
        basis = row["fulltext_artifact_version_id"]
        digest = uow.source_version.artifact_ref(basis)["content_hash"]
    material = replace(
        material,
        version_kind=SourceVersionKind.RETRACTED
        if change == "retract"
        else SourceVersionKind.CORRECTED,
        predecessor_source_version=FrozenSourceReference(source, row["content_hash"]),
        correction_basis_artifact=FrozenSourceReference(basis, digest),
    )
    versions = SourceVersionService(e["factory"], e["credentials"])
    created = versions.create(CreateSourceVersion(e["principal"], e["project"], material, uuid4()))
    versions.freeze(
        TransitionSourceVersion(
            e["principal"], e["project"], UUID(str(created["source_version_id"])), uuid4()
        )
    )
    assert e["service"].promote_strategy_question(e["principal"], cmd) == admitted
    assert (
        restart(e).get_strategy_capture(e["other"], ExactStrategyQuery(saved.id, e["project"]))
        == saved
    )
    with pytest.raises(ResearchBaseError) as denied:
        e["service"].promote_strategy_hypothesis(e["principal"], hcommand(e, saved))
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_history_survives_owning_source_merge_commands(b01_env):
    from researchbase.application.strategy_candidate_promotion import (
        CaptureNativeStrategyCommand,
        StrategyCandidatePromotionService,
    )
    from researchbase.persistence.uow import strategy_candidate_promotion_uow_factory
    from tests.integration.phase2.b01_support import merge_command
    from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

    e = b01_env
    factory = strategy_candidate_promotion_uow_factory(
        e["engine"].url.render_as_string(hide_password=False)
    )
    source = e["command"].source_version_id
    service = StrategyCandidatePromotionService(
        factory,
        e["service"]._credentials,
        e["service"]._store,
        ScriptedRAG(source, missing={"What limitations are reported for Recall?"}),
    )
    saved = service.capture_native_strategy(
        e["principal"], CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", (source,))
    )
    cmd = qcommand(e, saved)
    admitted = service.promote_strategy_question(e["principal"], cmd)
    e["bundle"].source_merge_execution.consume(merge_command(e))
    assert service.promote_strategy_question(e["principal"], cmd) == admitted
    assert (
        service.get_strategy_capture(e["principal"], ExactStrategyQuery(saved.id, e["project"]))
        == saved
    )
    with pytest.raises(ResearchBaseError) as denied:
        service.promote_strategy_hypothesis(e["principal"], hcommand(e, saved))
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
