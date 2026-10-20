"""Resolved local identities and explicit unresolved external intake; no provider activation."""

import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from researchbase.adapters.literature_http import HttpObservation
from researchbase.adapters.openalex import OpenAlexSearchCapability
from researchbase.application.scientific_rag_provider import FakeScientificRAGCapability
from tests.contracts import pr2_20_reports as r
from tests.contracts.pr2_20_evidence import digest_bytes
from tests.unit.phase2.test_pr2_06_openalex_offline_compat import payload
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import (
    context as rag_context,
)
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import (
    request as rag_request,
)
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import (
    response as rag_response,
)
from tests.unit.test_m2_openalex import context, request


def test_inventory_resolves_actual_source_lock_modes_and_unversioned_api():
    items = r.adapter_inventory()
    assert {item.mode for item in items} == {"TEST_ONLY", "DEFERRED", "METHOD_REFERENCE"}
    for item in items:
        assert item.material_provenance_path is not None
        assert item.local_source_sha256 == digest_bytes(
            Path(item.material_provenance_path).read_bytes()
        )
        assert item.lock_sha256 == digest_bytes(Path("uv.lock").read_bytes())
        assert item.license_sha256 is None and item.reviewed_at is None
        assert item.status == ("DEFERRED" if item.adapter_id == "paperqa2" else "BLOCKED")
        assert item.unresolved_items
        if item.adapter_id in {"openalex", "crossref"}:
            assert item.api_profile == "REST-unversioned"
            assert item.upstream_revision is None
        if item.adapter_id == "paperqa2":
            assert item.reason and r.B28_DISPOSITION in item.reason
        if item.mode in {"METHOD_REFERENCE", "DEFERRED"}:
            assert item.package_version is None
            with pytest.raises(ValueError):
                replace(item, status="PASS", reason=None)
    lock = tomllib.loads(Path("uv.lock").read_text())
    packages = {item["name"]: item["version"] for item in lock["package"]}
    assert packages["researchbase"] == "0.1.0"
    assert "paper-qa" not in packages and "paperqa" not in packages
    # Manifest/source identities, not upstream licenses, are resolved locally.
    assert len(r.migration_inventory()) >= 47
    assert r.migration_inventory()[-1]["revision"] == "0074_m1_manuscript_revision"


def test_offline_replacement_candidates_preserve_contract_and_do_not_enable_paperqa():
    from uuid import uuid4

    source = uuid4()
    first = FakeScientificRAGCapability(rag_response(source))
    second = FakeScientificRAGCapability(rag_response(source))
    assert first.answer(rag_request((source,)), rag_context()) == second.answer(
        rag_request((source,)), rag_context()
    )
    assert not any(hasattr(first, name) for name in ("engine", "session", "_factory"))
    a = OpenAlexSearchCapability(
        get=lambda *_: HttpObservation(200, {"content-type": "application/json"}, payload())
    )
    b = OpenAlexSearchCapability(
        get=lambda *_: HttpObservation(200, {"content-type": "application/json"}, payload())
    )
    first_result = a.search(request(), context())
    second_result = b.search(request(), context())
    assert first_result == replace(second_result, retrieved_at=first_result.retrieved_at)
    assert (
        next(item for item in r.adapter_inventory() if item.adapter_id == "paperqa2").status
        == "DEFERRED"
    )


def test_reference_entries_are_not_executable_pins_or_license_clearance():
    text = Path("harness.lock.yaml").read_text()
    assert "reference_only" in text or "reference-only" in text
    assert not any(Path(name).exists() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    assert all(item.license_sha256 is None for item in r.adapter_inventory())


def test_b17_benchmark_cases_are_bounded_and_do_not_expand_large_acceptance():
    from tests.e2e.test_pr2_20_benchmark import PACKAGE_CASES

    assert PACKAGE_CASES == (
        "package-first-freeze",
        "package-exact-replay",
        "package-consent-denied",
        "package-frozen-read",
    )


def test_complete_migration_chain_inventory_and_rendered_rows():
    items = r.migration_inventory()
    boundary = next(
        i for i, item in enumerate(items) if item["revision"] == "0068_b21_unresolved_capture"
    )
    assert boundary + 1 == 70
    assert items[0]["revision"] == "0001_empty"
    assert items[0]["down_revision"] is None
    assert len({item["revision"] for item in items}) == len(items)
    for previous, current in zip(items, items[1:], strict=False):
        assert current["down_revision"] == previous["revision"]
    table = r.migration_inventory_table(items)
    assert len(table.splitlines()) == len(items) + 2
    for item in items:
        assert sum(line.startswith(f"| {item['revision']} |") for line in table.splitlines()) == 1
        assert item["sha256"] == digest_bytes(Path(item["path"]).read_bytes())
