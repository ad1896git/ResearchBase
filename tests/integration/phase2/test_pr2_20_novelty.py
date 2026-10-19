"""Bounded correctness/parity; observed phantom regressions remain authoritative."""

from dataclasses import replace

import pytest

from tests.integration.phase2 import b18_novelty_support as b
from tests.integration.phase2 import pr2_20_support as s

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)
b18_env = b.b18_env


@pytest.mark.parametrize("kind", b.KINDS)
def test_bounded_first_write_replay_read_and_later_resolution(b18_env, kind):
    e = b18_env
    protected = b.protected_manifest(e)
    command = b.fresh_command(e, kind)
    first = b.invoke(e, kind, "first", command=command)
    after_first = s.manifest(e["engine"], b.NOVELTY_TABLES)
    for operation in ("replay", "read"):
        assert b.stable(b.invoke(e, kind, operation, command=command)) == b.stable(first)
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == after_first
    b.resolve_remaining(e)
    later = b.invoke(e, kind, "read", command=command)
    assert later.content_hash == first.content_hash
    if kind == "coverage":
        assert later.material_version == 2
        assert later.quality.captured_unresolved_result_count == 1
        assert later.quality.current_unresolved_result_count == 0
        assert b.stable(replace(later, quality=first.quality)) == b.stable(first)
    elif kind == "novelty":
        coverage = later.search_coverage
        assert coverage.material_version == 2
        assert coverage.quality.captured_unresolved_result_count == 1
        assert coverage.quality.current_unresolved_result_count == 0
        assert b.stable(replace(later, search_coverage=first.search_coverage)) == b.stable(first)
        assert coverage.content_hash == first.search_coverage.content_hash
        assert coverage.resolved_source_count == 1
    else:
        assert b.stable(later) == b.stable(first)
    assert s.manifest(e["engine"], b.NOVELTY_TABLES) == after_first
    assert b.protected_manifest(e) == protected
    assert len(b.PHANTOM_REFERENCES) == 2
    print("B18_PHANTOM_REFERENCES", b.PHANTOM_REFERENCES)
