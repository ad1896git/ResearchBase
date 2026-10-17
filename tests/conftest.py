from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("scripts.pr2_04_pytest_evidence",)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: requires a running PostgreSQL 18 service")
    config.addinivalue_line("markers", "phase1_golden: PR-17 Golden Scientific Acceptance")


@pytest.fixture(autouse=True)
def pr2_20_evidence_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test observations are disposable; reference evidence is never rewritten."""
    from tests.contracts import pr2_20_evidence

    monkeypatch.setattr(pr2_20_evidence, "EVIDENCE_ROOT", tmp_path)
