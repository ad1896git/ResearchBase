"""Retained-host overrides preserve exact bindings and fail-closed guards."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import URL

from researchbase.host_config import load_host_settings
from researchbase.runner import RunnerServer, resolve_runner_profile


def test_historical_defaults():
    host = load_host_settings({})
    assert str(host.durable_root) == "/Users/onephone/ResearchBaseData"
    assert str(host.trust_root) == "/Library/Application Support/ResearchBase"
    assert host.owner_uid == 502
    assert host.database_user == "onephone"
    assert host.socket_dir == "/private/tmp"
    assert host.database_port == "55440"
    assert host.runner_socket_dir == Path("/private/tmp")
    assert host.m3_database == "researchbase_m3_retained_20261011"
    assert host.m2_databases == tuple(
        f"researchbase_m2_{t}" for t in ("final", "live", "live2", "live3")
    )
    assert host.pgdata == host.durable_root / "rb-m2-pg"
    assert host.hba_file == host.pgdata / "pg_hba.conf"
    assert host.system_identifier == "7695048034454027996"
    assert host.m3_revision == "0031_m3_snapshot_relation_cardinality"


@pytest.fixture
def configured(monkeypatch, tmp_path):
    values = {
        "DURABLE_ROOT": str(tmp_path.resolve()),
        "TRUST_ROOT": str(tmp_path.resolve() / "policy"),
        "OWNER_UID": "501",
        "DATABASE_USER": "tester",
        "SOCKET_DIR": "/local/socket",
        "DATABASE_PORT": "5432",
        "RUNNER_SOCKET_DIR": str(tmp_path.resolve()),
        "M3_DATABASE": "custom_m3",
        "PGDATA": "/local/pgdata",
        "HBA_FILE": "/local/hba.conf",
        "SYSTEM_IDENTIFIER": "123456",
        "M3_REVISION": "custom_revision",
        **{f"M2_{t.upper()}_DATABASE": f"custom_{t}" for t in ("final", "live", "live2", "live3")},
    }
    for key, value in values.items():
        monkeypatch.setenv(f"RB_HOST_{key}", value)
    host = load_host_settings()
    for key in ("durable_root", "trust_root", "runner_socket_dir", "pgdata", "hba_file"):
        assert str(getattr(host, key)) == values[key.upper()]
    assert host.owner_uid == 501
    return host


def db_url(host, database):
    return URL.create(
        "postgresql+psycopg",
        username=host.database_user,
        database=database,
        query={"host": host.socket_dir, "port": host.database_port},
    )


def test_overridden_profiles_and_socket_parent(configured):
    host = configured
    for tag, db in zip(
        ("final", "live", "live2", "live3", "m3-retained"),
        (*host.m2_databases, host.m3_database),
        strict=True,
    ):
        prefix = "rb-m3-retained" if tag == "m3-retained" else f"rb-m2-{tag}"
        local = str(host.durable_root / f"{prefix}-installation")
        cas = str(host.durable_root / f"{prefix}-artifacts")
        url = db_url(host, db)
        profile = resolve_runner_profile(url.render_as_string(hide_password=False), local, cas)
        assert profile.tag == tag
        assert profile.policy_required == (tag == "m3-retained")
        for bad in (
            url.set(username="onephone"),
            url.set(password="secret"),
            url.set(host="localhost"),
            url.set(port=5432),
            url.set(query={"host": "/private/tmp", "port": "55440"}),
            url.set(database="researchbase_m3_retained_20261011"),
        ):
            with pytest.raises(ValueError):
                resolve_runner_profile(bad.render_as_string(hide_password=False), local, cas)
        with pytest.raises(ValueError):
            resolve_runner_profile(url.render_as_string(), local + "-other", cas)
    assert RunnerServer(object()).parent == host.runner_socket_dir
    assert RunnerServer(object(), parent=Path("/explicit")).parent == Path("/explicit")


def test_overridden_policy_path_still_uses_protected_reader(configured, monkeypatch):
    import researchbase.hg1_runtime as runtime

    seen = []
    monkeypatch.setattr(runtime, "read_trusted_config", lambda path: seen.append(path))
    assert runtime.build_hg1_coordinator("m3-retained", object(), object()) is None
    assert seen == [configured.trust_root / "hg1-02-m3-retained.json"]


def test_configured_owner_is_checked_before_composition(configured, monkeypatch):
    import researchbase.runner as runner

    monkeypatch.setattr(runner.sys, "argv", ["runner"])
    monkeypatch.setattr(runner, "process_uid", lambda: 502)
    with pytest.raises(SystemExit, match="configured trusted"):
        runner.main()

    from researchbase.persistence import config

    def stop_after_owner_check():
        raise RuntimeError("owner accepted")

    monkeypatch.setattr(runner, "process_uid", lambda: configured.owner_uid)
    monkeypatch.setattr(config, "load_settings", stop_after_owner_check)
    with pytest.raises(RuntimeError, match="owner accepted"):
        runner.main()


def test_overridden_server_facts_and_hba_still_fail_closed(configured, monkeypatch):
    import researchbase.hg1_runtime as runtime

    host = configured
    facts = [
        host.m3_database,
        host.database_user,
        str(host.pgdata),
        host.database_port,
        host.socket_dir,
        str(host.hba_file),
        "localhost",
        host.system_identifier,
        host.m3_revision,
    ]
    rules = [
        ("local", "all", host.database_user, None, None, "peer", None),
        *runtime.REQUIRED_M3_HBA[1:],
    ]
    disposed = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql):
            if "SET TRANSACTION READ ONLY" in str(sql):
                return None
            return SimpleNamespace(one=lambda: tuple(facts), all=lambda: rules)

    monkeypatch.setattr(
        runtime,
        "create_database_engine",
        lambda _: SimpleNamespace(connect=Connection, dispose=lambda: disposed.append(True)),
    )
    settings = SimpleNamespace(database_url=db_url(host, host.m3_database).render_as_string())
    runtime.verify_m3_server(settings)
    for index in range(len(facts)):
        original = facts[index]
        facts[index] = "unexpected"
        with pytest.raises(ValueError, match="identity changed"):
            runtime.verify_m3_server(settings)
        facts[index] = original
    rules[0] = (*rules[0][:5], "trust", None)
    with pytest.raises(ValueError, match="HBA changed"):
        runtime.verify_m3_server(settings)
    assert len(disposed) == 11


@pytest.mark.parametrize(
    "name,value",
    [
        ("OWNER_UID", "0"),
        ("OWNER_UID", "invalid"),
        ("DATABASE_PORT", "65536"),
        ("DATABASE_PORT", "abc"),
        ("DURABLE_ROOT", "relative"),
        ("DATABASE_USER", ""),
        ("SOCKET_DIR", " /tmp"),
        ("M3_DATABASE", "researchbase_m2_final"),
    ],
)
def test_invalid_overrides_fail_closed(name, value):
    with pytest.raises(ValueError):
        load_host_settings({f"RB_HOST_{name}": value})


@pytest.mark.parametrize(
    "script,stop,repo_default",
    [
        ("researchbase_host_review.sh", 'MODE=""', "/private/tmp/ResearchBase-phase2-recovered"),
        (
            "researchbase_host_pr2_03_verification.sh",
            "RUN_ID=",
            "/private/tmp/ResearchBase-phase2-recovered",
        ),
        (
            "researchbase_host_pr2_04_verification.sh",
            "for arg in",
            "/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/f2-p1-remediation",
        ),
    ],
)
def test_shell_defaults_and_overrides(script, stop, repo_default):
    source = (Path(__file__).resolve().parents[2] / "scripts" / script).read_text()
    prefix = source.split(stop, 1)[0]
    # Evaluate only declarations; historical acceptance scripts retain their live gates.
    expression = prefix + '\nprintf "%s\\n" "${EXPECTED_REPO:-$REPO}" "$REVIEW_TMP_ROOT"\n'
    clean = {key: value for key, value in os.environ.items() if not key.startswith("RB_REVIEW_")}
    result = subprocess.run(["bash", "-c", expression], env=clean, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [repo_default, "/private/tmp"]
    result = subprocess.run(
        ["bash", "-c", expression],
        env=dict(
            clean, RB_REVIEW_REPO="/custom/repo space", RB_REVIEW_TMP_ROOT="/custom/tmp space"
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["/custom/repo space", "/custom/tmp space"]
