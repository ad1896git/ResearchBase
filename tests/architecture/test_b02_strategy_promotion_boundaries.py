"""B02 layering and the bounded candidate-to-DRAFT boundary."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_domain_has_no_provider_persistence_or_store_dependencies():
    source = (ROOT / "src/researchbase/domain/strategy_candidate_promotion.py").read_text()
    imports = [n.module or "" for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)]
    assert all(
        not any(
            x in name
            for x in (
                "sqlalchemy",
                "fastapi",
                "application",
                "persistence",
                "artifact_store",
                "adapters",
            )
        )
        for name in imports
    )


def test_write_has_no_public_create_commit_or_external_work():
    source = (ROOT / "src/researchbase/application/strategy_candidate_promotion.py").read_text()
    tree = ast.parse(source)
    write = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_write")
    calls = [ast.unparse(n.func) for n in ast.walk(write) if isinstance(n, ast.Call)]
    assert not any(
        name.endswith(
            (
                ".execute",
                ".answer",
                ".create_research_question",
                ".create_hypothesis",
                ".put_verified",
            )
        )
        for name in calls
    )
    assert "uow.research_questions.add" in calls and "uow.hypotheses.add" in calls
    assert "actor_type" not in source
    assert "AgentExecution" not in source and "AgentPromotionRecord" not in source
    assert not any(
        name.startswith(("uow.claims", "uow.governance", "uow.runs", "uow.literature_evidence"))
        for name in calls
    )


def test_reads_have_no_explicit_locks_and_share_inventory_matches_contract():
    from researchbase.persistence.strategy_candidate_promotion_repository import S

    source = (
        ROOT / "src/researchbase/persistence/strategy_candidate_promotion_repository.py"
    ).read_text()
    assert "FOR UPDATE" not in source and "FOR SHARE" not in source
    assert S == tuple(sorted(S)) and len(S) == 19
    app = ast.parse(
        (ROOT / "src/researchbase/application/strategy_candidate_promotion.py").read_text()
    )
    read = next(n for n in ast.walk(app) if isinstance(n, ast.FunctionDef) and n.name == "_read")
    assert "read_only=True" in ast.unparse(read)
    assert not any(
        "prepare_write" in ast.unparse(n.func) for n in ast.walk(read) if isinstance(n, ast.Call)
    )


def test_exact_b02_child_and_only_four_approved_relations():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0079_agent_identity_versions"]
    assert (
        scripts.get_revision("0073_b02_strategy_admission").down_revision
        == "0072_b03_discussion_hypothesis"
    )
    tree = ast.parse((ROOT / "migrations/versions/0073_b02_strategy_admission.py").read_text())
    upgrade = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "upgrade"
    )
    statement = upgrade.body[0]
    assert isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
    sql = ast.literal_eval(statement.value.args[0]).lower()
    import re

    assert set(re.findall(r"create table (\w+)", sql)) == {
        "strategy_candidate_captures",
        "strategy_candidate_sources",
        "strategy_question_admissions",
        "strategy_hypothesis_admissions",
    }
    assert "alter table" not in sql and "cascade" not in sql
    assert "pg_current_xact_id()::xid" in sql and "pg_current_xact_id()::text" not in sql
