"""PR-17 Application/FastAPI/Typer semantic equivalence acceptance."""

from __future__ import annotations

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
    projections: dict[str, dict[str, object]] = {}
    for index, mode in enumerate(("cli", "application", "http")):
        with fresh_fixture(tmp_path / f"first-{index}", "gsas-01") as fixture:
            ids = run_workflow(fixture, mode)
            projections[mode] = normalized_projection(projection(fixture, ids))

    assert projections["application"] == projections["http"]
    assert projections["application"] == projections["cli"]
