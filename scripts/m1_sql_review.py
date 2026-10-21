"""Export the actual 0073→0074 function diffs from a disposable PostgreSQL DB.

Run from the repository root with RB_TEST_ADMIN_URL set:
    uv run python -m scripts.m1_sql_review
"""

from __future__ import annotations

import ast
import difflib
import os
import re
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/proposals/evidence/M1-S1-function-review"
MIGRATION = ROOT / "migrations/versions/0074_m1_manuscript_revision.py"
CATALOG_SQL = text(
    "SELECT p.proname, pg_get_functiondef(p.oid) FROM pg_proc p "
    "WHERE p.pronamespace='public'::regnamespace AND p.proname=ANY(:names) "
    "ORDER BY p.proname"
)


def main() -> None:
    tree = ast.parse(MIGRATION.read_text())
    upgrade = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "_UPGRADE"
    )
    names = sorted(
        set(re.findall(r"CREATE (?:OR REPLACE )?FUNCTION (?:public\.)?(\w+)\(", upgrade))
    )
    with (
        disposable_database("researchbase_pr212_test_") as url,
        patch.dict(os.environ, {"DATABASE_URL": url}),
    ):
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        engine = create_engine(url)
        try:
            command.upgrade(config, "0073_b02_strategy_admission")
            with engine.connect() as conn:
                before = dict(conn.execute(CATALOG_SQL, {"names": names}).all())
            command.upgrade(config, "0074_m1_manuscript_revision")
            with engine.connect() as conn:
                after = dict(conn.execute(CATALOG_SQL, {"names": names}).all())
            assert set(after) == set(names), (set(names) - set(after), set(after) - set(names))
            OUTPUT.mkdir(parents=True, exist_ok=True)
            inventory = []
            for name in names:
                previous = before.get(name, "")
                current = after[name]
                delta = "".join(
                    difflib.unified_diff(
                        previous.splitlines(keepends=True),
                        current.splitlines(keepends=True),
                        fromfile=f"0073/{name}.sql" if previous else "/dev/null",
                        tofile=f"0074/{name}.sql",
                        n=5,
                    )
                )
                # Blank context lines need no visible prefix in review artifacts.
                delta = "\n".join("" if line == " " else line for line in delta.splitlines())
                (OUTPUT / f"{name}.diff").write_text(
                    delta + "\n" if delta else "# Unchanged from 0073.\n"
                )
                inventory.append(f"{name}: {'changed' if previous else 'new'}")
            (OUTPUT / "b07_validate_revision.sql").write_text(after["b07_validate_revision"])
            (OUTPUT / "inventory.txt").write_text("\n".join(inventory) + "\n")
            print(
                f"Exported {len(names)} function diffs and the full revision validator to {OUTPUT}"
            )
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
