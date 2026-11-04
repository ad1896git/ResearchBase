"""`rb folder scan` registers newly seen files as literature sources, once, on real PostgreSQL."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from alembic import command
from alembic.config import Config


def test_scan_registers_new_files_once_and_skips_known_doi(phase2_database_url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    folder = tmp_path / "papers"
    folder.mkdir()
    (folder / "nap.txt").write_text("午睡综述\nDOI 10.7777/folder.test.1\n", encoding="utf-8")
    (folder / "copy.md").write_text("同一文献的另一份\n10.7777/folder.test.1\n", encoding="utf-8")
    (folder / "notes.md").write_text("没有 DOI 的笔记\n", encoding="utf-8")
    env = dict(
        os.environ,
        DATABASE_URL=phase2_database_url,
        RESEARCHBASE_LOCAL_ROOT=str(tmp_path / "installation"),
        ARTIFACT_STORE_ROOT=str(tmp_path / "artifacts"),
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
            "local", "bootstrap", "--display-name", "本人", "--project-name", "文件夹", "--json"
        ).splitlines()[-1]
    )["project_id"]

    first = rb("folder", "scan", str(folder), "--project-id", project)
    assert "已登记为文献 2 篇" in first
    # Files are taken in name order, so copy.md registers first and nap.txt is the duplicate.
    assert "同一 DOI 的文献已登记，未重复登记 1 个：nap.txt" in first

    second = rb("folder", "scan", str(folder), "--project-id", project)
    assert "已登记为文献" not in second
    listing = rb("paper", "list", "--project-id", project)
    assert "copy" in listing and "notes" in listing and "nap" not in listing
