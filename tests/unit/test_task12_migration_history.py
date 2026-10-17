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
    } == (
        set(pinned)
        | {
            "migrations/versions/0043_pr2_04_schema_contract.py",
            "migrations/versions/0044_pr2_15_revision_action.py",
            "migrations/versions/0045_pr2_16_basic_approval.py",
            "migrations/versions/0046_pr2_17_authorship_preparation.py",
            "migrations/versions/0047_pr2_18_novelty_prior_art.py",
            "migrations/versions/0048_b04_manuscript_freeze.py",
            "migrations/versions/0049_b05_manuscript_review.py",
            "migrations/versions/0050_b01_resolution_admission.py",
            "migrations/versions/0051_b06_revision_action.py",
            "migrations/versions/0052_b07_revision_decisions.py",
            "migrations/versions/0053_b08_issue_disposition.py",
            "migrations/versions/0054_b11_ready_for_submission.py",
        }
    )
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0054_b11_ready_for_submission"]
    assert (
        scripts.get_revision("0047_pr2_18_novelty_prior_art").down_revision
        == "0046_pr2_17_authorship"
    )
    assert (
        scripts.get_revision("0043_pr2_04_schema_contract").down_revision
        == "0042_pr2_15_minimal_decision"
    )
