from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
TOUCHED_TESTS = (
    ROOT / "tests/integration/test_pr12_closure.py",
    ROOT / "tests/integration/test_pr09_application.py",
    ROOT / "tests/integration/test_pr17dr_adversarial.py",
)


def test_pr17dr2_touched_tests_do_not_disable_all_triggers() -> None:
    broad_tokens = ("DISABLE TRIGGER ALL", "ENABLE TRIGGER ALL")

    assert [
        (path, token)
        for path in TOUCHED_TESTS
        for token in broad_tokens
        if token in path.read_text()
    ] == []
