from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: requires a running PostgreSQL 18 service")
    config.addinivalue_line("markers", "phase1_golden: PR-17 Golden Scientific Acceptance")
