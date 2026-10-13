"""Exact retained M3 Runner deployment binding, without a live host policy."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from researchbase.runner import resolve_runner_profile

ROOT = Path("/Users/onephone/ResearchBaseData")
M3 = "researchbase_m3_retained_20261011"


def url(database: str, *, query: str = "host=/private/tmp&port=55440") -> str:
    return f"postgresql+psycopg://onephone@/{database}?{query}"


def test_exact_retained_m3_profile_is_bound_to_approved_roots():
    profile = resolve_runner_profile(
        url(M3),
        str(ROOT / "rb-m3-retained-installation"),
        str(ROOT / "rb-m3-retained-artifacts"),
    )
    assert profile.tag == "m3-retained"
    assert profile.policy_required is True


@pytest.mark.parametrize("tag", ["final", "live", "live2", "live3"])
def test_existing_m2_profiles_remain_accepted(tag: str):
    profile = resolve_runner_profile(
        url(f"researchbase_m2_{tag}"),
        str(ROOT / f"rb-m2-{tag}-installation"),
        str(ROOT / f"rb-m2-{tag}-artifacts"),
    )
    assert profile.tag == tag
    assert profile.policy_required is False


@pytest.mark.parametrize(
    "database,installation,cas,query",
    [
        (
            M3,
            "rb-m2-final-installation",
            "rb-m3-retained-artifacts",
            "host=/private/tmp&port=55440",
        ),
        (
            M3,
            "rb-m3-retained-installation",
            "rb-m2-final-artifacts",
            "host=/private/tmp&port=55440",
        ),
        (
            "researchbase_m2_final",
            "rb-m3-retained-installation",
            "rb-m3-retained-artifacts",
            "host=/private/tmp&port=55440",
        ),
        (
            "researchbase_m3_other",
            "rb-m3-retained-installation",
            "rb-m3-retained-artifacts",
            "host=/private/tmp&port=55440",
        ),
        (
            M3,
            "rb-m3-retained-installation",
            "rb-m3-retained-artifacts",
            "host=/private/tmp&port=55442",
        ),
        (
            M3,
            "rb-m3-retained-installation",
            "rb-m3-retained-artifacts",
            "host=/private/tmp&port=55440&sslmode=disable",
        ),
        (
            M3,
            "rb-m3-retained-installation",
            "rb-m3-retained-artifacts",
            "host=127.0.0.1&port=55440",
        ),
    ],
)
def test_mismatched_or_unknown_profile_is_rejected(database, installation, cas, query):
    with pytest.raises(ValueError):
        resolve_runner_profile(
            url(database, query=query), str(ROOT / installation), str(ROOT / cas)
        )


def test_root_policy_tag_is_a_single_explicit_m3_name(monkeypatch):
    import researchbase.hg1_runtime as runtime

    seen = []
    monkeypatch.setattr(runtime, "read_trusted_config", lambda path: seen.append(path) or None)
    assert runtime.build_hg1_coordinator("m3-retained", object(), object()) is None
    assert seen == [runtime.TRUST_ROOT / "hg1-02-m3-retained.json"]
    with pytest.raises(ValueError):
        runtime.build_hg1_coordinator("m3-other", object(), object())


def test_m3_profile_requires_installed_policy_before_socket(monkeypatch):
    from researchbase.runner import require_coordinator

    profile = resolve_runner_profile(
        url(M3), str(ROOT / "rb-m3-retained-installation"), str(ROOT / "rb-m3-retained-artifacts")
    )
    with pytest.raises(ValueError):
        require_coordinator(profile, None)
    assert require_coordinator(profile, SimpleNamespace()) is not None


def test_client_identity_claims_still_fail_exact_v2_protocol():
    from researchbase.runner import BadRequest, _validate

    with pytest.raises(BadRequest):
        _validate({"v": 2, "op": "evidence.review", "project_id": "x", "actor_id": "owner"})


def test_m3_storage_rejects_symlinked_cas(tmp_path: Path, monkeypatch):
    import researchbase.runner as runner
    from researchbase.runner import RunnerProfile, verify_m3_storage

    tmp_path.chmod(0o700)
    monkeypatch.setattr(runner, "_DURABLE", tmp_path.resolve())
    installation = tmp_path.resolve() / "installation"
    actual_cas = tmp_path.resolve() / "actual-cas"
    installation.mkdir(mode=0o700)
    actual_cas.mkdir(mode=0o700)
    # First prove the private directories pass, so the rejection is the symlink.
    verify_m3_storage(RunnerProfile("m3-retained", installation, actual_cas, True))
    cas_link = tmp_path.resolve() / "cas"
    cas_link.symlink_to(actual_cas, target_is_directory=True)
    profile = RunnerProfile("m3-retained", installation, cas_link, True)
    with pytest.raises(ValueError):
        verify_m3_storage(profile)


def test_m3_server_identity_and_hba_are_checked_before_socket(monkeypatch):
    import researchbase.hg1_runtime as runtime

    expected = (
        "researchbase_m3_retained_20261011",
        "onephone",
        "/Users/onephone/ResearchBaseData/rb-m2-pg",
        "55440",
        "/private/tmp",
        "/Users/onephone/ResearchBaseData/rb-m2-pg/pg_hba.conf",
        "127.0.0.1",
        "7695048034454027996",
        "0031_m3_snapshot_relation_cardinality",
    )
    hba = runtime.REQUIRED_M3_HBA

    class Connection:
        def __init__(self, facts):
            self.facts = facts

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql):
            value = str(sql)
            if "SET TRANSACTION READ ONLY" in value:
                return None
            if "pg_hba_file_rules" in value:
                return SimpleNamespace(all=lambda: hba)
            return SimpleNamespace(one=lambda: self.facts)

    class Engine:
        def __init__(self, facts):
            self.facts = facts

        def connect(self):
            return Connection(self.facts)

        def dispose(self):
            pass

    monkeypatch.setattr(runtime, "create_database_engine", lambda _url: Engine(expected))
    runtime.verify_m3_server(SimpleNamespace(database_url=url(M3)))
    bad: list[str] = list(expected)
    bad[7] = "wrong-system-id"
    monkeypatch.setattr(runtime, "create_database_engine", lambda _url: Engine(tuple(bad)))
    with pytest.raises(ValueError):
        runtime.verify_m3_server(SimpleNamespace(database_url=url(M3)))
    monkeypatch.setattr(runtime, "create_database_engine", lambda _url: Engine(expected))
    monkeypatch.setattr(runtime, "REQUIRED_M3_HBA", ())
    with pytest.raises(ValueError):
        runtime.verify_m3_server(SimpleNamespace(database_url=url(M3)))
