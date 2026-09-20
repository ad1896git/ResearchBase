from __future__ import annotations

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).parents[2]


def test_ci_migration_head_assertion_matches_repository_head() -> None:
    repository_head = ScriptDirectory.from_config(
        Config(str(ROOT / "alembic.ini"))
    ).get_current_head()
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    match = re.search(r'alembic current \| tail -n 1\)" = "([^"]+)"', workflow)

    assert match is not None
    assert match.group(1) == f"{repository_head} (head)"
