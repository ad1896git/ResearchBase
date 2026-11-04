"""Reference imports and metadata corrections on real PostgreSQL (no network)."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_bib_import_and_paper_correct_append_versions(phase2_database_url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    folder = tmp_path / "papers"
    folder.mkdir()
    (folder / "first.txt").write_text("午睡综述正文\n10.7777/bib.test.1\n", encoding="utf-8")
    (folder / "second.txt").write_text("另一篇的正文\n10.7777/bib.test.2\n", encoding="utf-8")
    env = dict(
        os.environ,
        DATABASE_URL=phase2_database_url,
        RESEARCHBASE_LOCAL_ROOT=str(tmp_path / "installation"),
        ARTIFACT_STORE_ROOT=str(tmp_path / "artifacts"),
        RESEARCHBASE_PAPERS_DIR=str(folder),
        RESEARCHBASE_CROSSREF_LOOKUP="0",
    )

    def rb(*args):
        run = subprocess.run(
            [sys.executable, "-m", "researchbase.cli.main", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, (run.stdout, run.stderr)
        return run.stdout

    rb("local", "init", "--json")
    project = json.loads(
        rb(
            "local", "bootstrap", "--display-name", "本人", "--project-name", "文献", "--json"
        ).splitlines()[-1]
    )["project_id"]
    rb("folder", "scan", "--project-id", project)  # registers first.txt and second.txt

    # Added after the scan, so this file is not registered yet.
    (folder / "third.txt").write_text("第三篇的正文\n10.7777/bib.test.3\n", encoding="utf-8")
    bib = tmp_path / "library.bib"
    bib.write_text(
        "@article{a,\n  title = {午睡综述（正式版）},\n  author = {Li, Hua and Wang, Ming},\n"
        "  journal = {Sleep Review},\n  volume = {5},\n  doi = {10.7777/bib.test.1}\n}\n"
        "@article{b,\n  title = {Second paper, corrected},\n  journal = {Memory Letters},\n"
        "  doi = {10.7777/bib.test.2}\n}\n"
        "@article{c,\n  title = {Third paper from the export},\n"
        "  doi = {10.7777/bib.test.3}\n}\n"
        "@article{d,\n  title = {Not in the folder},\n  doi = {10.9999/none.1}\n}\n",
        encoding="utf-8",
    )

    first = rb("folder", "import-refs", str(bib), "--project-id", project)
    # first.txt and second.txt are already registered; third.txt was registered by the scan
    # just before matching, and the bib entry then corrects its title.
    assert "新增 0 篇，追加更正 3 篇，无变化 0 篇" in first
    assert "Not in the folder" in first

    again = rb("folder", "import-refs", str(bib), "--project-id", project)
    assert "新增 0 篇，追加更正 0 篇，无变化 3 篇" in again

    rb(
        "paper",
        "correct",
        "午睡综述（正式版）",
        "--venue",
        "Sleep Review Online",
        "--reason",
        "期刊名更正",
        "--project-id",
        project,
    )

    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        versions = connection.execute(
            text(
                "SELECT v.version_number, v.version_kind, v.status FROM source_versions v "
                "WHERE v.literature_source_id = ("
                "  SELECT literature_source_id FROM source_versions "
                "  WHERE title = '午睡综述（正式版）' LIMIT 1"
                ") ORDER BY v.version_number"
            )
        ).all()
    engine.dispose()
    assert [tuple(row) for row in versions] == [
        (1, "PUBLISHED", "SUPERSEDED"),
        (2, "CORRECTED", "SUPERSEDED"),
        (3, "CORRECTED", "FROZEN"),
    ]

    listing = rb("paper", "list", "--project-id", project)
    assert "Third paper from the export" in listing

    evidence = rb(
        "evidence",
        "add",
        "--paper",
        "午睡综述（正式版）",
        "--quote",
        "午睡综述正文",
        "--project-id",
        project,
    )
    assert "已添加文献证据" in evidence
