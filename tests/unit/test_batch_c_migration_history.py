"""Pin B09 bytes and the owner-authorized B10 compatibility revision."""

import hashlib
import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]


def test_batch_c_linear_history_and_frozen_lane_sql():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    chain = (
        "0054_b11_ready_for_submission",
        "0055_b09_approval_tuples",
        "0056_b10_reconsideration",
        "0057_xid_wraparound_guards",
        "0058_b12_prepare_submission",
    )
    assert scripts.get_heads() == [chain[-1]]
    for parent, child in zip(chain, chain[1:], strict=False):
        assert scripts.get_revision(child).down_revision == parent
    pinned = {
        "0055_b09_approval_tuples": (
            "a190d1e687e8e715edf6a86acb623d6d563d4169ceaa51050ca09531aae420b9"
        ),
        "0056_b10_reconsideration": (
            "ef002d66e9e5b028c17a7ea6c6ca2eeb9366a8a4377f7b19d1376fbd0ac98f9a"
        ),
    }
    for revision, digest in pinned.items():
        source = (ROOT / "migrations/versions" / f"{revision}.py").read_text()
        normalized = re.sub(r"^(?:revision|down_revision) = .*\n", "", source, flags=re.M)
        assert hashlib.sha256(normalized.encode()).hexdigest() == digest
