"""HG1-02 is enabled only by a protected host-admin policy file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchbase.hg1_runtime import read_trusted_config


def test_missing_admin_config_leaves_hg1_01_runner_unchanged(tmp_path: Path):
    assert read_trusted_config(tmp_path / "absent.json") is None


def test_user_owned_config_cannot_grant_operator_authority(tmp_path: Path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"version": 1, "operator_uid": 503}))
    path.chmod(0o600)
    with pytest.raises(PermissionError):
        read_trusted_config(path)
