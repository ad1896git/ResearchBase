from __future__ import annotations

from scripts.pr18_evidence import (
    TODO_DISPOSITIONS,
    audit_repository_markers,
)


def test_repository_marker_audit_classifies_all_authorized_marker_forms() -> None:
    audit = audit_repository_markers()
    assert audit["markers_searched"] == ["TODO", "FIXME", "XXX", "HACK", "TBD"]
    assert audit["records"]
    assert all(record["category"] for record in audit["records"])
    assert all(record["disposition"] in TODO_DISPOSITIONS for record in audit["records"])
    assert all(record["rationale"] for record in audit["records"])
    assert all(record["surrounding_intent"] for record in audit["records"])
    assert all(record["class_group_id"] for record in audit["records"])


def test_repository_marker_audit_has_no_live_undisposed_or_architecture_blockers() -> None:
    audit = audit_repository_markers()
    assert audit["undisposed_live"] == []
    assert audit["architecture_p0"] == []
    assert audit["architecture_p1"] == []


def test_repository_marker_audit_is_stable_across_repeated_generation() -> None:
    first = audit_repository_markers()
    second = audit_repository_markers()
    assert first == second


def test_repository_marker_audit_is_not_a_blanket_generic_disposition() -> None:
    records = audit_repository_markers()["records"]
    assert len({record["rationale"] for record in records}) >= 3
    assert len({record["class_group_id"] for record in records}) >= 3
    assert not all(record["disposition"] == "INTENTIONAL_NONBLOCKING" for record in records)
