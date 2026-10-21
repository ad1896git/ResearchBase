"""Bounded local effect owners and literal lock protocols; SQL witnesses live in owner suites."""

import ast
import inspect
from pathlib import Path

import pytest

from researchbase.application.approval import ApprovalService
from researchbase.application.prepared_submission import PreparedSubmissionService
from researchbase.application.publication import PublicationService
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.persistence.approval_repository import (
    B09_DECIDE_SHARE_SQL,
    B09_SHARE_SQL,
    B09_SNAPSHOT_TABLES,
    B13_APPROVAL_SQL,
    B13_SHARE_SQL,
    B13_SNAPSHOT_TABLES,
    SqlAlchemyApprovalRepository,
)
from researchbase.persistence.prepared_submission_repository import (
    B17_SHARE_SQL,
    B17_SNAPSHOT_TABLES,
    SqlAlchemyPreparedSubmissionRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

ROOT = Path(__file__).resolve().parents[2]
# Literal ordered inventory from the approved guide; deliberately independent of code constants.
SCIENTIFIC_TABLES = tuple(
    """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions measurements
metric_definition_versions metric_definitions project_membership_events project_memberships
project_role_assignments projects review_issue_events review_issues run_artifact_inputs
run_dataset_inputs runs scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions statistical_result_inputs
statistical_results
""".split()
)
AUTHORSHIP_TABLES = (
    "authorship_snapshot_authors",
    "authorship_snapshot_contributions",
    "authorship_snapshot_corresponding_authors",
    "authorship_snapshot_equal_groups",
    "authorship_snapshots",
    "contribution_records",
)


def test_literal_write_inventories_and_first_statement_owners():
    assert B13_SNAPSHOT_TABLES == SCIENTIFIC_TABLES
    assert B09_SNAPSHOT_TABLES == tuple(sorted((*SCIENTIFIC_TABLES, "publications")))
    assert B17_SNAPSHOT_TABLES == tuple(sorted((*SCIENTIFIC_TABLES, *AUTHORSHIP_TABLES)))
    assert B13_SHARE_SQL == "LOCK TABLE " + ",".join(SCIENTIFIC_TABLES) + " IN SHARE MODE"
    assert (
        B09_SHARE_SQL
        == "LOCK TABLE " + ",".join(sorted((*SCIENTIFIC_TABLES, "publications"))) + " IN SHARE MODE"
    )
    assert B09_DECIDE_SHARE_SQL == B13_SHARE_SQL
    assert (
        B17_SHARE_SQL
        == "LOCK TABLE "
        + ",".join(sorted((*SCIENTIFIC_TABLES, *AUTHORSHIP_TABLES)))
        + " IN SHARE MODE"
    )
    assert (
        B13_APPROVAL_SQL
        == "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE"
    )
    for method, first in (
        (SqlAlchemyApprovalRepository.lock_snapshot, "B09_DECIDE_SHARE_SQL"),
        (SqlAlchemyApprovalRepository.prepare_write, "B13_SHARE_SQL"),
        (SqlAlchemyPreparedSubmissionRepository.prepare_freeze_write, "B17_SHARE_SQL"),
    ):
        source = inspect.getsource(method)
        assert source.index(first) < source.index("LOCK TABLE publications")
        assert source.index(first) < source.index(
            "_timeouts()" if "_timeouts()" in source else "SET LOCAL"
        )


@pytest.mark.parametrize(
    "method,delegate",
    [
        (
            ScientificConclusionService.record_internal_scientific_release,
            "._release(",
        ),
        (
            PublicationService.transition_publication_ready,
            "_consume_ready_in_uow(uow, principal, command)",
        ),
        (PreparedSubmissionService.freeze_prepared_submission, "_consume_package_in_uow("),
    ],
)
def test_shared_application_boundary_and_local_effect(method, delegate):
    source = inspect.getsource(method)
    assert delegate in source
    for token in (
        "actor_type ==",
        '"HUMAN"',
        '"AGENT"',
        "httpx.",
        "requests.",
        ".send(",
        ".dispatch(",
    ):
        assert token not in source


@pytest.mark.parametrize(
    "owner", ["approval", "scientific_conclusion", "publication", "prepared_submission"]
)
def test_effect_owners_have_no_transport_or_infrastructure_dependencies(owner):
    for layer in ("domain", "application"):
        name = "manuscript" if layer == "domain" and owner == "publication" else owner
        tree = ast.parse((ROOT / f"src/researchbase/{layer}/{name}.py").read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(
            name.startswith(
                (
                    "httpx",
                    "requests",
                    "urllib",
                    "socket",
                    "smtplib",
                    "subprocess",
                    "redis",
                    "celery",
                    "sqlalchemy",
                    "fastapi",
                    "typer",
                    "researchbase.persistence",
                )
            )
            for name in imports
        )


@pytest.mark.parametrize(
    "method",
    [
        ApprovalService._prepare_read,
        ApprovalService._consumption_read,
        ApprovalService._receipt_view,
        PublicationService._read_ready,
        PublicationService._ready_readback,
        PreparedSubmissionService._freeze_replay,
        PreparedSubmissionService._read,
    ],
)
def test_formal_read_roots_have_no_exclusion_or_mutation(method):
    source = inspect.getsource(method)
    for token in (
        "LOCK TABLE",
        "pg_advisory",
        "FOR UPDATE",
        "FOR SHARE",
        ".commit(",
        "prepare_write(",
        "prepare_freeze_write(",
        "lock_scope(",
        "lock_grant(",
        "terminalize(",
        "admission=True",
        "insert_consumption(",
    ):
        assert token not in source


def test_transaction_modes_remain_distinct():
    read = inspect.getsource(SqlAlchemyUnitOfWork.begin_formal_read)
    assert '"isolation_level": "REPEATABLE READ"' in read
    assert '"postgresql_readonly": True' in read
    assert '"SERIALIZABLE" if consuming else "READ COMMITTED"' in inspect.getsource(
        SqlAlchemyUnitOfWork.configure_grant_transaction
    )
    assert "self.configure_revision_transaction()" in inspect.getsource(
        SqlAlchemyUnitOfWork.configure_approval_transaction
    )
    assert '"READ COMMITTED"' in inspect.getsource(
        SqlAlchemyUnitOfWork.configure_revision_transaction
    )
    assert '"SERIALIZABLE"' in inspect.getsource(
        SqlAlchemyPreparedSubmissionRepository.prepare_freeze_write
    )
