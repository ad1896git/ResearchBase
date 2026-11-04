"""`rb correct` appends correction records on real PostgreSQL, and the export shows them."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_correction_is_appended_and_exported(phase2_database_url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    env = dict(
        os.environ,
        DATABASE_URL=phase2_database_url,
        RESEARCHBASE_LOCAL_ROOT=str(tmp_path / "installation"),
        ARTIFACT_STORE_ROOT=str(tmp_path / "artifacts"),
    )

    def rb(*args, ok=True):
        run = subprocess.run(
            [sys.executable, "-m", "researchbase.cli.main", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert (run.returncode == 0) == ok, (run.returncode, run.stdout, run.stderr)
        return run.stdout if ok else run.stderr

    rb("local", "init", "--json")
    boot = json.loads(
        rb(
            "local",
            "bootstrap",
            "--display-name",
            "本人",
            "--project-name",
            "更正测试",
            "--json",
        ).splitlines()[-1]
    )
    project = boot["project_id"]
    rb("question", "add", "午睡是否改善次日记忆", "--project-id", project)
    rb("conclusion", "add", "午睡可能改善次日记忆", "--project-id", project)

    first = rb(
        "correct",
        "--conclusion",
        "1",
        "--assertion",
        "午睡可能改善次日记忆（样本量小）",
        "--reason",
        "原结论未写样本量",
        "--project-id",
        project,
    )
    assert "已添加更正 #1（更正对象：结论 #1）" in first

    refused = rb(
        "correct",
        "--conclusion",
        "1",
        "--result",
        "1",
        "--assertion",
        "x",
        "--reason",
        "y",
        "--project-id",
        project,
        ok=False,
    )
    assert "只指定一个要更正的对象" in refused

    second = rb(
        "correct",
        "--conclusion",
        "1",
        "--assertion",
        "需要重复验证",
        "--reason",
        "第二次更正",
        "--project-id",
        project,
    )
    assert "已添加更正 #2" in second

    export = tmp_path / "export.md"
    rb("export", "--out", str(export), "--project-id", project)
    markdown = export.read_text(encoding="utf-8")
    assert "- 更正 #1：午睡可能改善次日记忆（样本量小）（原因：原结论未写样本量）" in markdown
    assert "## 更正记录" in markdown
    assert "（更正对象：结论；原因：第二次更正）" in markdown

    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT target_type, correction_type, corrected_assertion #>> '{}' "
                "FROM correction_records WHERE project_id = :project ORDER BY created_at"
            ),
            {"project": project},
        ).all()
    engine.dispose()
    assert [row[0] for row in rows] == ["CLAIM_VERSION", "CLAIM_VERSION"]
    assert [row[1] for row in rows] == ["FACTUAL", "FACTUAL"]
    assert rows[-1][2] == "需要重复验证"
