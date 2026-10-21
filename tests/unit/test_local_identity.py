import json
import os
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from researchbase.foundation.errors import ResearchBaseError


def test_real_os_identity_and_protected_installation(tmp_path, monkeypatch):
    from researchbase.local_identity import LocalIdentityAdapter

    monkeypatch.setenv("USER", "forged-owner")
    monkeypatch.setenv("SUDO_UID", "0")
    adapter = LocalIdentityAdapter.initialize(tmp_path / "installation")
    subject = adapter.subject()
    assert subject.subject_value == str(os.geteuid())
    assert subject.subject_kind == "OS_UID"
    assert adapter.is_valid(subject, datetime.now(UTC))
    assert not adapter.is_valid(replace(subject, subject_value="999999"), datetime.now(UTC))
    assert not adapter.is_valid(
        replace(subject, deployment_id="another-installation"), datetime.now(UTC)
    )
    assert (adapter.root / "installation.json").stat().st_mode & 0o777 == 0o600
    assert adapter.root.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ResearchBaseError):
        LocalIdentityAdapter.initialize(adapter.root)


@pytest.mark.parametrize("mode", [0o644, 0o666])
def test_insecure_config_refused(tmp_path, mode):
    from researchbase.local_identity import LocalIdentityAdapter

    adapter = LocalIdentityAdapter.initialize(tmp_path / "installation")
    subject = adapter.subject()
    (adapter.root / "installation.json").chmod(mode)
    assert not adapter.is_valid(subject, datetime.now(UTC))


def test_revoked_expired_foreign_machine_and_symlink_refused(tmp_path, monkeypatch):
    from researchbase.local_identity import LocalIdentityAdapter

    adapter = LocalIdentityAdapter.initialize(tmp_path / "installation")
    subject = adapter.subject()
    p = adapter.root / "installation.json"
    original = p.read_text()
    for patch in (
        {"enabled": False},
        {"not_after": "2000-01-01T00:00:00+00:00"},
        {"machine": "foreign"},
    ):
        value = json.loads(original)
        value.update(patch)
        p.write_text(json.dumps(value))
        assert not adapter.is_valid(subject, datetime.now(UTC))
    p.write_text(original)
    p.rename(adapter.root / "saved.json")
    p.symlink_to(adapter.root / "saved.json")
    with pytest.raises(ResearchBaseError):
        adapter.subject()


def test_privilege_transition_denied(tmp_path, monkeypatch):
    from researchbase.local_identity import LocalIdentityAdapter

    adapter = LocalIdentityAdapter.initialize(tmp_path / "installation")
    subject = adapter.subject()
    monkeypatch.setattr(os, "geteuid", lambda: os.getuid() + 1)
    assert not adapter.is_valid(subject, datetime.now(UTC))


def test_bootstrap_proof_integrity_and_one_use_secret(tmp_path):
    from researchbase.local_identity import LocalIdentityAdapter

    adapter = LocalIdentityAdapter.initialize(tmp_path / "installation")
    authority = adapter.bootstrap_authority()
    assert adapter.verify(authority)
    assert not adapter.verify(replace(authority, proof_sha256="0" * 64))
    adapter.invalidate(authority)
    assert not (adapter.root / "bootstrap.secret").exists()
    assert not adapter.verify(authority)


def test_copied_installation_and_root_execution_are_refused(tmp_path, monkeypatch):
    import shutil

    from researchbase.local_identity import LocalIdentityAdapter

    adapter = LocalIdentityAdapter.initialize(tmp_path / "original")
    shutil.copytree(adapter.root, tmp_path / "copy")
    with pytest.raises(ResearchBaseError):
        LocalIdentityAdapter(tmp_path / "copy").subject()
    monkeypatch.setattr(os, "getuid", lambda: 0)
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    with pytest.raises(ResearchBaseError):
        adapter.subject()
