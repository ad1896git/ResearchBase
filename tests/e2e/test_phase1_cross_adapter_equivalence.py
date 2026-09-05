"""PR-17 Application/FastAPI/Typer semantic equivalence acceptance."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from tests.e2e.support import fresh_fixture, normalized_projection, projection, run_workflow

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


@pytest.mark.parametrize("mode", ("http", "cli"))
def test_adapter_gsas_01_projection_matches_direct_application(
    tmp_path: Path,
    mode: str,
) -> None:
    with fresh_fixture(tmp_path / "application", "gsas-01") as application_fixture:
        application_ids = run_workflow(application_fixture, "application")
        application_projection = normalized_projection(
            projection(application_fixture, application_ids)
        )

    with fresh_fixture(tmp_path / mode, "gsas-01") as adapter_fixture:
        adapter_ids = run_workflow(adapter_fixture, mode)
        adapter_projection = normalized_projection(projection(adapter_fixture, adapter_ids))

    assert adapter_projection == application_projection


def test_adapter_order_independence_uses_independent_fresh_fixtures(tmp_path: Path) -> None:
    orders = {
        "cli-application-http": ("cli", "application", "http"),
        "http-cli-application": ("http", "cli", "application"),
    }
    for order_name, order in orders.items():
        projections: dict[str, dict[str, object]] = {}
        for index, mode in enumerate(order):
            with fresh_fixture(tmp_path / f"{order_name}-{index}", "gsas-01") as fixture:
                ids = run_workflow(fixture, mode)
                projections[mode] = normalized_projection(projection(fixture, ids))

        assert projections["application"] == projections["http"]
        assert projections["application"] == projections["cli"]


def test_projection_integrity_preserves_observed_semantic_differences() -> None:
    observed = {
        "_reference_roles": {
            "11111111-1111-1111-1111-111111111111": "run",
            "22222222-2222-2222-2222-222222222222": "dataset",
            "33333333-3333-3333-3333-333333333333": "artifact",
        },
        "transport": {"request_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        "run": {
            "id": "11111111-1111-1111-1111-111111111111",
            "status": "SUCCEEDED",
            "dataset_inputs": ["22222222-2222-2222-2222-222222222222"],
        },
        "trace_paths": [("measurement", "supports", "run")],
    }

    generated_id_variant = deepcopy(observed)
    generated_id_variant["_reference_roles"] = {
        "44444444-4444-4444-4444-444444444444": "run",
        "22222222-2222-2222-2222-222222222222": "dataset",
        "33333333-3333-3333-3333-333333333333": "artifact",
    }
    generated_id_variant["run"]["id"] = "44444444-4444-4444-4444-444444444444"
    generated_id_variant["transport"]["request_id"] = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert normalized_projection(generated_id_variant) == normalized_projection(observed)

    changed_status = deepcopy(observed)
    changed_status["run"]["status"] = "FAILED"
    assert normalized_projection(changed_status) != normalized_projection(observed)

    changed_input = deepcopy(observed)
    changed_input["run"]["dataset_inputs"] = ["33333333-3333-3333-3333-333333333333"]
    assert normalized_projection(changed_input) != normalized_projection(observed)

    changed_path = deepcopy(observed)
    changed_path["trace_paths"] = [("statistical_result", "supports", "run")]
    assert normalized_projection(changed_path) != normalized_projection(observed)
