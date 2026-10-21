"""PR2-18 owns only immutable literature judgments through Application commands."""

import ast
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]


def test_domain_import_boundary():
    tree = ast.parse((ROOT / "src/researchbase/domain/novelty.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not any(
                x in (node.module or "")
                for x in (
                    "persistence",
                    "sqlalchemy",
                    "fastapi",
                    "typer",
                    "adapters",
                    "application",
                )
            )


def test_no_provider_call_in_transaction():
    tree = ast.parse((ROOT / "src/researchbase/application/novelty.py").read_text())
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls.intersection(
        {
            "observe",
            "execute_search",
            "invoke_model",
            "consume",
            "approve",
            "create_review",
            "resolve_issue",
            "transition_ready",
            "import_document",
        }
    )


def test_no_new_semantic_json_owner():
    ddl = (ROOT / "migrations/versions/0047_pr2_18_novelty_prior_art.py").read_text()
    tables = {part.split("(")[0].strip() for part in ddl.split("CREATE TABLE ")[1:]}
    assert tables == {
        "search_coverage",
        "search_coverage_executions",
        "prior_art_relations",
        "prior_art_evidence_inputs",
        "novelty_assessments",
    }
    assert "ON DELETE CASCADE" not in ddl
    assert "target_type VARCHAR" not in ddl


def test_common_principal_boundary():
    routes = (ROOT / "src/researchbase/api/routes.py").read_text()
    cli = (ROOT / "src/researchbase/cli/commands/literature.py").read_text()
    for method in (
        "record_search_coverage",
        "record_prior_art_relation",
        "record_novelty_assessment",
        "read_search_coverage",
        "read_prior_art_relation",
        "read_novelty_assessment",
    ):
        assert f"def {method}(" in routes and f"def {method}(" in cli
    assert "_verified_principal(request)" in routes
    assert "_principal(runtime), command" in cli


def test_literature_source_not_evidence():
    from uuid import uuid4

    import pytest

    from researchbase.domain.novelty import HashRef, PriorArtKind, prior_art_material

    with pytest.raises(ValueError):
        prior_art_material(
            HashRef("ClaimVersion", uuid4(), "a" * 64),
            HashRef("SourceVersion", uuid4(), "b" * 64),
            PriorArtKind.RELATED,
            "A source alone is insufficient.",
            (),
            uuid4(),
        )


def test_search_result_not_evidence():
    from uuid import uuid4

    import pytest

    from researchbase.domain.novelty import HashRef

    with pytest.raises(ValueError):
        HashRef(cast(Any, "SearchResultRecord"), uuid4(), "a" * 64)


def test_citation_not_claim_support():
    from researchbase.persistence.novelty_repository import _TABLES

    assert set(_TABLES.values()) == {
        "search_coverage",
        "prior_art_relations",
        "novelty_assessments",
    }


def test_strategy_does_not_import_persistence():
    tree = ast.parse((ROOT / "src/researchbase/application/novelty.py").read_text())
    assert not any(
        isinstance(node, ast.ImportFrom) and ".persistence" in (node.module or "")
        for node in ast.walk(tree)
    )


def test_adapter_does_not_write_db():
    tree = ast.parse((ROOT / "src/researchbase/api/routes.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "record_search_coverage",
            "record_prior_art_relation",
            "record_novelty_assessment",
        }:
            names = {
                x.func.attr
                for x in ast.walk(node)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
            }
            assert "execute" not in names and "commit" not in names


def test_no_storm_specific_core_schema():
    assert (
        "storm"
        not in (ROOT / "migrations/versions/0047_pr2_18_novelty_prior_art.py").read_text().lower()
    )


def test_no_paperqa_specific_core_schema():
    assert (
        "paperqa"
        not in (ROOT / "migrations/versions/0047_pr2_18_novelty_prior_art.py").read_text().lower()
    )


def test_discussion_not_canonical_science():
    tree = ast.parse((ROOT / "src/researchbase/application/novelty.py").read_text())
    assert not any(
        isinstance(node, ast.Attribute) and node.attr == "discussion" for node in ast.walk(tree)
    )


def test_manuscript_not_scientific_source_of_truth():
    from uuid import uuid4

    import pytest

    from researchbase.domain.novelty import HashRef

    with pytest.raises(ValueError):
        HashRef(cast(Any, "ManuscriptVersion"), uuid4(), "a" * 64)


def test_review_does_not_mutate_target():
    repo = (ROOT / "src/researchbase/persistence/novelty_repository.py").read_text()
    assert "UPDATE claim_versions" not in repo
    assert "UPDATE source_versions" not in repo
    assert "UPDATE literature_evidence" not in repo


def test_decision_does_not_mutate_history():
    ddl = (ROOT / "migrations/versions/0047_pr2_18_novelty_prior_art.py").read_text()
    assert "BEFORE UPDATE OR DELETE ON {table}" in ddl
    assert "EXECUTE FUNCTION pr218_immutable()" in ddl


def test_approval_does_not_override_invalid_fact():
    from uuid import uuid4

    import pytest

    from researchbase.application.novelty import RecordNoveltyAssessmentCommand
    from researchbase.domain.novelty import NoveltyOutcome

    with pytest.raises(TypeError):
        RecordNoveltyAssessmentCommand(
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            NoveltyOutcome.INCONCLUSIVE,
            "Limited.",
            **cast(Any, {"approval_grant_id": uuid4()}),
        )


def test_external_call_not_inside_long_db_transaction():
    test_no_provider_call_in_transaction()
