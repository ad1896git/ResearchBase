"""Task 12 may add exactly one revision; every preexisting migration stays sealed."""

import hashlib
import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]


def test_task12_preserves_every_historical_migration_byte_and_exact_child():
    pinned = json.loads(
        (ROOT / "docs/verification/task12/historical-migration-sha256.json").read_text()
    )
    for name, digest in pinned.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert {
        str(path.relative_to(ROOT)) for path in (ROOT / "migrations/versions").glob("*.py")
    } == (set(pinned) | {"migrations/versions/0043_pr2_04_schema_contract.py"})
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0043_pr2_04_schema_contract"]
    assert (
        scripts.get_revision(scripts.get_heads()[0]).down_revision == "0042_pr2_15_minimal_decision"
    )
