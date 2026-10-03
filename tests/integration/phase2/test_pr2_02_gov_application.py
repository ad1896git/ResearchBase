from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_01_source_identity import (
    _authorized_service,
    _frozen_basis,
)

from researchbase.application.source_identity import AddSourceIdentifier, RegisterLiteratureSource
from researchbase.application.source_merge import (
    DecideSourceMerge,
    ProposeSourceMerge,
    RevokeSourceMergeApproval,
    SourceMergeGovernanceService,
)
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class _ValidCredential:
    def is_valid(self, principal, at):
        return True


class _ExpiringCredential:
    def __init__(self) -> None:
        self.deadline: datetime | None = None
        self.authorization_times: list[datetime] = []

    def is_valid(self, principal, at):
        del principal
        self.authorization_times.append(at)
        return self.deadline is None or at < self.deadline


def test_proposal_requires_human_owner_and_decisions_are_basis_bound(
    phase2_database_url: str,
) -> None:
    engine, identity, literature, principal, project_id = _authorized_service(phase2_database_url)
    source_a = literature.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Source A", uuid4())
    )["source_id"]
    source_b = literature.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Source B", uuid4())
    )["source_id"]
    second_project_id = identity.create_project_with_owner(
        principal, name="Second affected project", request_id=uuid4()
    )
    with engine.begin() as connection:
        for source_id in (source_a, source_b):
            connection.execute(
                text(
                    "INSERT INTO literature_source_project_links"
                    "(id,literature_source_id,project_id,linked_by,linked_at) "
                    "VALUES (:id,:source,:project,:actor,clock_timestamp())"
                ),
                {
                    "id": uuid4(),
                    "source": UUID(str(source_id)),
                    "project": second_project_id,
                    "actor": principal.actor_id,
                },
            )
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    service = SourceMergeGovernanceService(
        lambda: SqlAlchemyUnitOfWork(factory), _ValidCredential()
    )
    evidence_id = _frozen_basis(engine, project_id, principal.actor_id)
    with pytest.raises(ResearchBaseError) as duplicate_evidence:
        service.propose(
            ProposeSourceMerge(
                principal,
                project_id,
                UUID(str(source_a)),
                UUID(str(source_b)),
                UUID(str(source_b)),
                "Duplicate evidence input",
                uuid4(),
                None,
                (evidence_id, evidence_id),
            )
        )
    assert duplicate_evidence.value.code is ErrorCode.VALIDATION_ERROR
    request_id = uuid4()
    proposal = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_b)),
            "Duplicate DOI record",
            request_id,
            None,
            (evidence_id,),
        )
    )
    with pytest.raises(IntegrityError, match="consumed proposal requires all project approvals"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_merge_governance_events"
                    "(id,proposal_id,approval_id,project_id,actor_id,event_kind,occurred_at,reason,"
                    "deployment_id,request_id,request_hash,basis_hash,command_name) "
                    "VALUES (:id,:proposal,NULL,:project,:actor,'PROPOSAL_CONSUMED',"
                    "clock_timestamp(),'invalid premature consume',:deployment,:request,"
                    ":request_hash,"
                    ":basis,'CONSUME_SOURCE_MERGE_PROPOSAL')"
                ),
                {
                    "id": uuid4(),
                    "proposal": UUID(str(proposal["proposal_id"])),
                    "project": project_id,
                    "actor": principal.actor_id,
                    "deployment": principal.deployment_id,
                    "request": uuid4(),
                    "request_hash": "b" * 64,
                    "basis": proposal["proposal_basis_hash"],
                },
            )
    with pytest.raises(IntegrityError, match="event required fields or basis are invalid"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_merge_governance_events"
                    "(id,proposal_id,project_id,actor_id,event_kind,occurred_at,reason,deployment_id,"
                    "request_id,request_hash,basis_hash,command_name) "
                    "VALUES (:id,:proposal,:project,:actor,'PROPOSAL_STALE',clock_timestamp(),"
                    "'basis changed',:deployment,:request,:hash,"
                    ":wrong_basis,'MARK_SOURCE_MERGE_PROPOSAL_STALE')"
                ),
                {
                    "id": uuid4(),
                    "proposal": UUID(str(proposal["proposal_id"])),
                    "project": project_id,
                    "actor": principal.actor_id,
                    "deployment": principal.deployment_id,
                    "request": uuid4(),
                    "hash": "b" * 64,
                    "wrong_basis": "c" * 64,
                },
            )
    replay = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_b)),
            "Duplicate DOI record",
            request_id,
            None,
            (evidence_id,),
        )
    )
    assert replay == proposal
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM source_merge_proposal_projects WHERE proposal_id=:id"),
                {"id": UUID(str(proposal["proposal_id"]))},
            ).scalar_one()
            == 2
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM source_merge_proposal_evidence WHERE proposal_id=:id"),
                {"id": UUID(str(proposal["proposal_id"]))},
            ).scalar_one()
            == 1
        )

    shared_request_id = uuid4()
    decision = service.decide(
        DecideSourceMerge(
            principal, project_id, UUID(str(proposal["proposal_id"])), "APPROVE", shared_request_id
        )
    )
    assert decision["decision"] == "APPROVE"
    assert (
        service.decide(
            DecideSourceMerge(
                principal,
                project_id,
                UUID(str(proposal["proposal_id"])),
                "APPROVE",
                shared_request_id,
            )
        )
        == decision
    )
    second_approval = service.decide(
        DecideSourceMerge(
            principal,
            second_project_id,
            UUID(str(proposal["proposal_id"])),
            "APPROVE",
            shared_request_id,
        )
    )
    assert second_approval["decision"] == "APPROVE"
    replacement = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_a)),
            "Canonical direction reassessed",
            uuid4(),
            UUID(str(proposal["proposal_id"])),
        )
    )
    assert (
        service.get(principal, project_id, UUID(str(proposal["proposal_id"])))["status"]
        == "SUPERSEDED"
    )
    assert replacement["proposal_basis_hash"] != proposal["proposal_basis_hash"]
    revocable = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_b)),
            "Revocation behavior",
            uuid4(),
        )
    )
    for decision_project in (project_id, second_project_id):
        service.decide(
            DecideSourceMerge(
                principal,
                decision_project,
                UUID(str(revocable["proposal_id"])),
                "APPROVE",
                uuid4(),
            )
        )
    service.revoke(
        RevokeSourceMergeApproval(
            principal,
            project_id,
            UUID(str(revocable["proposal_id"])),
            "Owner withdrew approval",
            uuid4(),
        )
    )
    assert (
        service.get(principal, project_id, UUID(str(revocable["proposal_id"])))["status"] == "STALE"
    )
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT decision_basis_hash FROM source_merge_approvals WHERE id=:id"),
                {"id": UUID(str(decision["approval_id"]))},
            ).scalar_one()
            == proposal["proposal_basis_hash"]
        )

    reject_proposal = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_a)),
            "Direction reconsidered",
            uuid4(),
        )
    )
    rejected = service.decide(
        DecideSourceMerge(
            principal,
            project_id,
            UUID(str(reject_proposal["proposal_id"])),
            "REJECT",
            shared_request_id,
            "Human review found the records distinct",
        )
    )
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT decision,decision_reason,decision_payload_hash "
                "FROM source_merge_approvals WHERE id=:id"
            ),
            {"id": UUID(str(rejected["approval_id"]))},
        ).one()
    assert row.decision == "REJECT"
    assert row.decision_reason == "Human review found the records distinct"
    assert len(row.decision_payload_hash) == 64

    stale_proposal = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_b)),
            "Basis will change",
            uuid4(),
        )
    )
    stale_decision_request = uuid4()
    saved_stale_basis_decision = service.decide(
        DecideSourceMerge(
            principal,
            project_id,
            UUID(str(stale_proposal["proposal_id"])),
            "APPROVE",
            stale_decision_request,
        )
    )
    literature.add_source_identifier(
        AddSourceIdentifier(
            principal,
            project_id,
            UUID(str(source_a)),
            IdentifierType.DOI,
            "10.5555/source-merge-stale",
            True,
            uuid4(),
        )
    )
    assert (
        service.decide(
            DecideSourceMerge(
                principal,
                project_id,
                UUID(str(stale_proposal["proposal_id"])),
                "APPROVE",
                stale_decision_request,
            )
        )
        == saved_stale_basis_decision
    )
    with pytest.raises(ResearchBaseError) as stale:
        service.decide(
            DecideSourceMerge(
                principal,
                project_id,
                UUID(str(stale_proposal["proposal_id"])),
                "APPROVE",
                uuid4(),
            )
        )
    assert stale.value.code is ErrorCode.SOURCE_MERGE_PROPOSAL_STALE
    with pytest.raises(ResearchBaseError) as repeated_stale:
        service.decide(
            DecideSourceMerge(
                principal,
                project_id,
                UUID(str(stale_proposal["proposal_id"])),
                "APPROVE",
                uuid4(),
            )
        )
    assert repeated_stale.value.code is ErrorCode.SOURCE_MERGE_PROPOSAL_STALE
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM source_merge_governance_events "
                    "WHERE proposal_id=:id AND event_kind='PROPOSAL_STALE'"
                ),
                {"id": UUID(str(stale_proposal["proposal_id"]))},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_owner_credential_expiry_during_authority_lock_wait_denies_approval(
    phase2_database_url: str,
) -> None:
    credential = _ExpiringCredential()
    engine, _, literature, principal, project_id = _authorized_service(
        phase2_database_url, credential
    )
    source_a = literature.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Expiry A", uuid4())
    )["source_id"]
    source_b = literature.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Expiry B", uuid4())
    )["source_id"]
    service = SourceMergeGovernanceService(
        lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False)), credential
    )
    proposal = service.propose(
        ProposeSourceMerge(
            principal,
            project_id,
            UUID(str(source_a)),
            UUID(str(source_b)),
            UUID(str(source_b)),
            "Expiry lock test",
            uuid4(),
        )
    )
    blocker = engine.connect()
    try:
        blocker.execute(
            text("SELECT id FROM actors WHERE id=:actor FOR UPDATE"),
            {"actor": principal.actor_id},
        )
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        credential.deadline = blocker.execute(
            text("SELECT clock_timestamp() + interval '750 milliseconds'")
        ).scalar_one()
        command = DecideSourceMerge(
            principal, project_id, UUID(str(proposal["proposal_id"])), "APPROVE", uuid4()
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(service.decide, command)
            wait_confirmed = False
            timeout_at = time.monotonic() + 10
            while time.monotonic() < timeout_at:
                wait_confirmed = bool(
                    blocker.execute(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_locks "
                            "WHERE pid<>:blocker_pid AND NOT granted)"
                        ),
                        {"blocker_pid": blocker_pid},
                    ).scalar_one()
                )
                database_now = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
                if wait_confirmed and database_now > credential.deadline:
                    break
            blocker.commit()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(timeout=10)
        assert wait_confirmed
        deadline = credential.deadline
        assert deadline is not None
        assert credential.authorization_times[-1] >= deadline
        assert denied.value.code is ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM source_merge_approvals WHERE proposal_id=:id"),
                    {"id": UUID(str(proposal["proposal_id"]))},
                ).scalar_one()
                == 0
            )
    finally:
        blocker.rollback()
        blocker.close()
        engine.dispose()
