"""Exact retained M3 must not silently activate an unreviewed live provider."""

import pytest

from researchbase.cli.composition import _search_capabilities


def _url(name: str) -> str:
    return f"postgresql+psycopg://onephone@/{name}?host=/private/tmp&port=55440"


def test_retained_m3_denies_live_openalex_even_with_injected_key():
    registry = _search_capabilities(_url("researchbase_m3_retained_20261011"), "secret-canary")
    assert registry.resolve("openalex", "works-v1") is None
    assert registry.versions("openalex") == ()


@pytest.mark.parametrize("tag", ("final", "live", "live2", "live3"))
def test_accepted_m2_profile_registration_is_unchanged(tag: str):
    registry = _search_capabilities(_url(f"researchbase_m2_{tag}"), None)
    adapter = registry.resolve("openalex", "works-v1")
    assert adapter is not None
    assert adapter.capability_id == "openalex"
    assert adapter.version == "works-v1"


def test_disposable_database_registration_is_unchanged():
    registry = _search_capabilities(_url("researchbase_test_disposable"), None)
    assert registry.resolve("openalex", "works-v1") is not None
