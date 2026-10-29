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
        "0059_b13_grant_consumption",
        "0060_b15_package_preparation",
        "0061_b16_consent_withdrawal",
        "0062_b14a_publication_entry",
        "0063_b14r_ready_approval",
        "0064_b14_publication_ready",
        "0065_b22_prior_art_correction",
        "0066_b19_close_prior_art_basis",
        "0067_b17_prepared_package_freeze",
        "0068_b21_unresolved_capture",
        "0069_b13_stale_gate_denials",
        "0070_b20_screening_basis",
        "0071_b23_novelty_review",
        "0072_b03_discussion_hypothesis",
        "0073_b02_strategy_admission",
        "0074_m1_manuscript_revision",
        "0075_m1_reconsideration",
        "0076_agent_runtime_bootstrap",
        "0077_research_task_graph",
        "0078_task_safety_policies",
        "0079_agent_identity_versions",
        "0080_capability_gateway",
        "0081_agent_execution_intents",
        "0082_experiment_search_core",
        "0083_bearing_evaluation_guards",
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
