"""PR-17 GSAS-01 positive workflow and repeated fresh-fixture acceptance."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.e2e.support import fresh_fixture, normalized_projection, projection, run_workflow

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


def test_gsas_01_direct_application_is_complete_and_non_trivial(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-01") as fixture:
        ids = run_workflow(fixture, "application")
        result = projection(fixture, ids)

    assert result["research"] == {
        "rq_status": "FROZEN",
        "hypothesis_status": "FROZEN",
        "spec_status": "FROZEN",
    }
    assert result["run"]["status"] == "SUCCEEDED"
    assert result["run"]["dataset_input_count"] == 1
    assert result["run"]["artifact_input_count"] == 1
    assert result["run"]["measurement_count"] == 2
    assert result["run"]["closure"][0] is True
    assert [item["target_id"] for item in result["run"]["dataset_inputs"]] == [
        str(ids.dataset_snapshot_id)
    ]
    assert [item["target_id"] for item in result["run"]["artifact_inputs"]] == [
        str(ids.artifact_version_id)
    ]
    assert result["inputs"]["experiment_spec_version"] == str(ids.experiment_spec_version_id)
    assert result["inputs"]["metric_definition_version"] == str(ids.metric_definition_version_id)
    assert result["observations"]["measurement_count"] == 2
    assert result["observations"]["statistical_result_count"] == 1
    assert result["observations"]["statistical_inputs"] == [
        ("primary", 0, str(ids.measurement_ids[0])),
        ("replicate", 1, str(ids.measurement_ids[1])),
    ]
    assert {
        (
            item["measurement_id"],
            item["statistical_result_id"],
            item["relation_type"],
            item["qualification"],
        )
        for item in result["claim"]["evidence_relations"]
    } == {
        (str(ids.measurement_ids[0]), None, "supports", "direct measurement"),
        (None, str(ids.statistical_result_id), "supports", "multi-input statistic"),
    }
    assert result["claim"]["support_set_hash"]
    assert result["claim"]["content_hash"]
    assert result["claim"]["status"] == "FROZEN"
    assert result["claim"]["evidence_count"] == 2
    assert result["claim"]["closure"][0] is True
    assert len(result["claim"]["trace_runs"]) == 1
    assert len(result["claim"]["trace_paths"]) == 3
    assert result["governance"]["finding_target"][:2] == ("run", str(ids.run_id))
    assert result["governance"]["impact_targets"] == [
        ("claim_version", str(ids.claim_version_id), "downstream"),
        ("measurement", str(ids.measurement_ids[0]), "downstream"),
        ("run", str(ids.run_id), "direct"),
        ("statistical_result", str(ids.statistical_result_id), "downstream"),
    ]
    assert result["governance"]["correction"]["target_id"] == str(ids.measurement_ids[0])
    assert result["governance"]["validity"][0] == "invalid"
    assert result["governance"]["impact_paths"]


def test_gsas_01_repeated_independent_fresh_postgresql_fixtures_match(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path / "first", "gsas-01") as first_fixture:
        first_ids = run_workflow(first_fixture, "application")
        first = normalized_projection(projection(first_fixture, first_ids))

    with fresh_fixture(tmp_path / "second", "gsas-01") as second_fixture:
        second_ids = run_workflow(second_fixture, "application")
        second = normalized_projection(projection(second_fixture, second_ids))

    assert first == second
