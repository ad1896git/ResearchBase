"""B08 additive event admission and unchanged canonical hash contracts."""

import inspect
from pathlib import Path

from researchbase.application.internal_review import InternalReviewService
from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_owner_admission_and_exact_mapping_dependency():
    proposal = (ROOT / "docs/proposals/B08_Issue_Disposition_Contract_DRAFT.md").read_text()
    adr = (ROOT / "docs/architecture/adr/ADR-0016-b08-issue-disposition.md").read_text()
    b07 = (
        ROOT / "docs/architecture/adr/ADR-0015-b07-revision-decisions-concern-carry-forward.md"
    ).read_text()
    assert "APPROVED by owner 2026-10-16 — first slice authorized for implementation" in proposal
    for name in ("decision_revision_concerns", "revision_action_re_reviews"):
        assert name in b07
    assert "Registry 03" in adr and "Field Contract 13" in adr
    assert "not cryptographically bound" in adr


def test_one_forward_event_refinement_and_no_parallel_state():
    source = (ROOT / "migrations/versions/0053_b08_issue_disposition.py").read_text()
    assert 'down_revision = "0052_b07_revision_decisions"' in source
    for forbidden in (
        "CREATE TABLE",
        "ON DELETE CASCADE",
        "ADD COLUMN content_hash",
        "ExternalEffect",
    ):
        assert forbidden not in source
    assert "fk_b08_event_mapping" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    # M1 §12.2: disposition excludes the two written issue tables from B09.
    assert len(REVISION_SNAPSHOT_TABLES) == 44


def test_application_reads_configure_snapshot_before_authentication_and_never_lock():
    for method in (
        InternalReviewService.get_issue_history,
        InternalReviewService.get_issue_disposition,
    ):
        source = inspect.getsource(method)
        assert source.index("configure_revision_transaction(readonly=True)") < source.index(
            "_disposition_authorize"
        )
        assert source.count("self._factory()") == 1
        assert "lock_" not in source
    source = inspect.getsource(InternalReviewService._disposition_authorize)
    assert 'row["actor_type"] == "HUMAN"' in source
    assert "clock" not in source  # fresh database time comes from the shared port
