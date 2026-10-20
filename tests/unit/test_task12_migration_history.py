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
            "migrations/versions/0055_b09_approval_tuples.py",
            "migrations/versions/0056_b10_reconsideration.py",
            "migrations/versions/0057_xid_wraparound_guards.py",
            "migrations/versions/0058_b12_prepare_submission.py",
            "migrations/versions/0059_b13_grant_consumption.py",
            "migrations/versions/0060_b15_package_preparation.py",
            "migrations/versions/0061_b16_consent_withdrawal.py",
            "migrations/versions/0062_b14a_publication_entry.py",
            "migrations/versions/0063_b14r_ready_approval.py",
            "migrations/versions/0064_b14_publication_ready.py",
            "migrations/versions/0065_b22_prior_art_correction.py",
            "migrations/versions/0066_b19_close_prior_art_basis.py",
            "migrations/versions/0067_b17_prepared_package_freeze.py",
            "migrations/versions/0068_b21_unresolved_capture.py",
            "migrations/versions/0069_b13_stale_gate_denials.py",
            "migrations/versions/0070_b20_screening_basis.py",
            "migrations/versions/0071_b23_novelty_review.py",
            "migrations/versions/0072_b03_discussion_hypothesis.py",
            "migrations/versions/0073_b02_strategy_admission.py",
            "migrations/versions/0074_m1_manuscript_revision.py",
            "migrations/versions/0075_m1_reconsideration.py",
        }
    )
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0075_m1_reconsideration"]
    assert (
        scripts.get_revision("0047_pr2_18_novelty_prior_art").down_revision
        == "0046_pr2_17_authorship"
    )
    assert (
        scripts.get_revision("0043_pr2_04_schema_contract").down_revision
        == "0042_pr2_15_minimal_decision"
    )
