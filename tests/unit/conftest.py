"""Unit-test isolation: never read the developer's local identity root.

The CLI composition root looks for a local identity folder (default
``~/.researchbase-local``). On a machine where the owner has bootstrapped
the local tool, that folder exists, and composition tests would try to
authenticate against the real local database. CI has no such folder, so
the tests only behaved differently on the developer's machine. Point the
root at a path that does not exist, so unit tests see a fresh, empty setup.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def local_identity_root_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(tmp_path / "local-root-absent"))
