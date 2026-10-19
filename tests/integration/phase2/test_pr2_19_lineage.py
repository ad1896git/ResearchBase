"""F1 prefixes and F1b: exact history survives correction and retraction."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.scientific_conclusion import ClaimInputRequest, LiteratureInputRequest
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts, upgrade_head
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_candidate_env as _pr219_candidate_env
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _pr219_evidence_env
from tests.integration.phase2.test_b05_manuscript_review import b04_env as _b04_env
from tests.integration.phase2.test_b05_manuscript_review import b05_env as _b05_env
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

pytestmark = pytest.mark.integration


def material(env, kind=SourceVersionKind.CORRECTED):
    literature, _, _, _, source, _, document, _, _ = env
    with literature._factory() as uow:
        row = uow.source_version.version(source)
    return SourceVersionMaterial(
        row["literature_source_id"],
        kind,
        FrozenSourceReference(source, row["content_hash"]),
        FrozenSourceReference(UUID(document["artifact_version_id"]), document["content_hash"]),
        "PR219 lineage",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize("fault", ["missing", "wrong_source", "unfrozen", "bad_basis"])
def test_lineage_rejection_has_zero_delta(pr219_candidate_env, fault):
    env, sources = pr219_candidate_env
    service = SourceVersionService(env[0]._factory, env[8])
    value = material(env)
    if fault == "missing":
        value = replace(value, predecessor_source_version=FrozenSourceReference(uuid4(), "a" * 64))
    elif fault == "wrong_source":
        with env[0]._factory() as uow:
            row = uow.source_version.version(sources[1])
        value = replace(
            value, predecessor_source_version=FrozenSourceReference(sources[1], row["content_hash"])
        )
    elif fault == "unfrozen":
        draft = service.create(
            CreateSourceVersion(
                env[1],
                env[3],
                replace(
                    value,
                    version_kind=SourceVersionKind.PUBLISHED,
                    predecessor_source_version=None,
                    correction_basis_artifact=None,
                ),
                uuid4(),
            )
        )
        value = replace(
            value,
            predecessor_source_version=FrozenSourceReference(
                UUID(str(draft["source_version_id"])), "a" * 64
            ),
        )
    else:
        value = replace(value, correction_basis_artifact=FrozenSourceReference(uuid4(), "a" * 64))
    before = counts(env[7])
    with pytest.raises(ResearchBaseError) as denied:
        service.create(CreateSourceVersion(env[1], env[3], value, uuid4()))
    assert denied.value.code is (
        ErrorCode.FROZEN_REFERENCE_REQUIRED
        if fault == "bad_basis"
        else ErrorCode.INVALID_SOURCE_VERSION_LINEAGE
    )
    assert counts(env[7]) == before


@pytest.mark.parametrize("kind", [SourceVersionKind.CORRECTED, SourceVersionKind.RETRACTED])
@pytest.mark.parametrize("path", ["direct", "claim_snapshot"])
def test_lineage_preserves_exact_bytes_and_blocks_new_support(conclusion_env, kind, path):
    scientific, _, literature, author, reviewer, project, claim, source, engine, credentials = (
        conclusion_env
    )
    upgrade_head(engine)
    evidence = literature.create(author, project, source, "improved recall", uuid4())
    eid = UUID(evidence["id"])
    literature.review(
        reviewer, project, eid, "VERIFIED", "Independent exact-byte inspection", uuid4()
    )
    edges = [{"evidence_id": str(eid), "relation_type": "SUPPORTS", "qualification": "Exact span"}]
    snapshot = literature.snapshot(author, project, "ClaimVersion", claim, edges, uuid4())
    claims = (
        (ClaimInputRequest(claim, "SUPPORTS", UUID(snapshot["id"])),)
        if path == "claim_snapshot"
        else ()
    )
    direct = (LiteratureInputRequest(eid, "SUPPORTS"),) if path == "direct" else ()
    target = scientific.create(
        author, project, "PR219 exact literature", SCOPE, "WEAK", None, claims, direct, uuid4()
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    old = scientific.read(author, project, target.conclusion_id, target.version_id)
    with engine.connect() as conn:
        hashes = conn.execute(
            text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
            {"id": claim},
        ).one()
        source_row = conn.execute(
            text(
                "SELECT literature_source_id,content_hash,fulltext_artifact_version_id FROM "
                "source_versions WHERE id=:id"
            ),
            {"id": source},
        ).one()
        artifact_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": source_row[2]}
        ).scalar_one()
    value = SourceVersionMaterial(
        source_row[0],
        kind,
        FrozenSourceReference(source, source_row[1]),
        FrozenSourceReference(source_row[2], artifact_hash),
        "PR219 upstream update",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    versions = SourceVersionService(literature._factory, credentials)
    created = versions.create(CreateSourceVersion(author, project, value, uuid4()))
    versions.freeze(
        TransitionSourceVersion(author, project, UUID(str(created["source_version_id"])), uuid4())
    )
    current = scientific.read(author, project, target.conclusion_id, target.version_id)
    assert (current.content_hash, current.support_set_hash) == (
        old.content_hash,
        old.support_set_hash,
    )
    assert current.validity != "VALID"
    assert (
        literature.get_snapshot(author, project, UUID(snapshot["id"]))["content_hash"]
        == snapshot["content_hash"]
    )
    assert (
        literature.get(author, project, eid)["extracted_statement"]
        == evidence["extracted_statement"]
    )
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
                {"id": claim},
            ).one()
            == hashes
        )
    denied_before = counts(engine)
    with pytest.raises(ResearchBaseError) as denied:
        scientific.create(
            author, project, "Invalid new admission", SCOPE, "WEAK", None, claims, direct, uuid4()
        )
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(engine) == denied_before
    with pytest.raises(ResearchBaseError) as denied:
        literature.snapshot(author, project, "ClaimVersion", claim, edges, uuid4())
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert counts(engine) == denied_before
    assert (
        scientific.read(author, project, target.conclusion_id, target.version_id).content_hash
        == old.content_hash
    )
    assert (
        literature._store.open(artifact_hash)
        == b"A measured effect improved recall.\n\nLimitations remain."
    )


def test_concurrent_corrections_cannot_fork_current_lineage(pr219_evidence_env):
    env = pr219_evidence_env
    service = SourceVersionService(env[0]._factory, env[8])
    value = material(env)
    drafts = [
        service.create(
            CreateSourceVersion(env[1], env[3], replace(value, title=f"Correction {i}"), uuid4())
        )
        for i in range(2)
    ]

    def freeze(draft):
        try:
            return service.freeze(
                TransitionSourceVersion(
                    env[1], env[3], UUID(str(draft["source_version_id"])), uuid4()
                )
            )
        except ResearchBaseError as error:
            return error

    from tests.integration.phase2.pr2_19_support import _wait_for_pg_blocker

    held, release = Event(), Event()
    pids = []

    def pause(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.lstrip().upper().startswith("UPDATE SOURCE_VERSIONS SET STATUS='FROZEN'")
            and not held.is_set()
        ):
            pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15)

    event.listen(env[7], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(freeze, drafts[0])
            try:
                assert held.wait(10)
                second = pool.submit(freeze, drafts[1])
                witness = _wait_for_pg_blocker(env[7], pids[0], "advisory")
                assert witness["pid"] != pids[0] and not second.done()
            finally:
                release.set()
            results = [first.result(timeout=10), second.result(timeout=10)]
        assert isinstance(results[0], dict)
        assert isinstance(results[1], ResearchBaseError)
        assert results[1].code is ErrorCode.INVALID_SOURCE_VERSION_LINEAGE
        with env[7].connect() as conn:
            assert conn.execute(
                text("SELECT current_version_id FROM literature_sources WHERE id=:id"),
                {"id": value.literature_source_id},
            ).scalar_one() == UUID(str(drafts[0]["source_version_id"]))
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM source_versions WHERE literature_source_id=:id "
                        "AND status='FROZEN'"
                    ),
                    {"id": value.literature_source_id},
                ).scalar_one()
                == 1
            )
    finally:
        release.set()
        event.remove(env[7], "after_cursor_execute", pause)


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_evidence_env = _pr219_evidence_env


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("kind", ["CORRECTED", "RETRACTED"])
def test_current_manuscript_projection_audit_retains_frozen_material(b05_env, snapshot, kind):
    from tests.integration.phase2.b25_support import (
        literature_conclusion,
        queries,
        source_transition,
    )
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
    from tests.integration.phase2.test_b05_manuscript_review import seal

    env = b05_env
    evidence, support, conclusion = literature_conclusion(env, snapshot=snapshot)
    sealed = seal(env)
    service, q, aq = queries(env)
    initial = service.get_manuscript_audit(env[3], aq)
    assert initial.validity.current_validity == "VALID"
    with env[5].connect() as conn:
        document_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": sealed.document_artifact_version_id},
        ).scalar_one()
    document_bytes = env[7].open(document_hash)
    source_transition(env, kind)
    service, q, aq = queries(env)  # Fresh owning readers.
    with sql_protocol(env[5]) as observed:
        current = service.get_manuscript_validity(env[3], q)
        audit = service.get_manuscript_audit(env[3], aq)
    assert_snapshot_read(observed)
    assert current.current_validity == ("INVALID" if kind == "RETRACTED" else "STALE")
    assert (
        current.content_hash == sealed.content_hash
        and current.placement_set_hash == sealed.placement_set_hash
    )
    assert audit.validity.content_hash == current.content_hash
    assert audit.validity.witnesses == current.witnesses
    witness = next(w for w in current.witnesses if w.node.kind == "LiteratureEvidence")
    assert witness.node.id == evidence
    assert witness.occurrences[0].nodes[1].id == conclusion
    if snapshot:
        assert support in {node.id for node in witness.occurrences[0].nodes}
    assert env[7].verify(document_hash) and env[7].open(document_hash) == document_bytes
    # No automatic finding/impact assertion: the source owner supplies lineage.
    assert audit.unsupported_concerns == ()


b04_env = _b04_env

b05_env = _b05_env


@pytest.mark.parametrize("snapshot", [False, True], ids=["direct", "claim-snapshot"])
@pytest.mark.parametrize("kind", ["CORRECTED", "RETRACTED"])
@pytest.mark.parametrize("stage", ["ready-pending", "prepared", "frozen"])
def test_f1_current_downstream_facts_preserve_saved_consumptions(b05_env, snapshot, kind, stage):
    from researchbase.application.publication import GetPublicationReadyTransitionQuery
    from tests.integration.phase2.b17_fixtures import build, next_package
    from tests.integration.phase2.b25_support import (
        literature_conclusion,
        queries,
        source_transition,
    )
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
    from tests.integration.phase2.pr2_19_support import (
        fresh_package_service,
        fresh_publication_service,
    )
    from tests.integration.phase2.test_b14_publication_ready import issued

    env = b05_env
    literature_conclusion(env, snapshot=snapshot)
    f: Any = None
    command: Any
    if stage == "ready-pending":
        app, command, approval, _ = issued(env)
        saved = None
    else:
        f = build(env)
        app = fresh_publication_service(env)
        command, approval = f.ready_command, f.approval
        saved = approval.get_grant_consumption(env[2], command.project_id, command.command_key)
    frozen = (
        f.app.freeze_prepared_submission(f.actor, f.command) if f and stage == "frozen" else None
    )
    package: Any = f.app.get_prepared_submission(f.actor, f.query) if f else None
    pending: Any = next_package(f) if frozen else None
    # Retain every saved scientific hash and its exact local CAS bytes, independent
    # of the current read projections. Counts alone cannot prove immutability.
    with env[5].connect() as conn:
        historical = {
            table: conn.execute(text(f"SELECT * FROM {table} ORDER BY id")).all()
            for table in (
                "literature_evidence",
                "literature_support_snapshots",
                "claim_versions",
                "scientific_conclusion_versions",
                "manuscript_versions",
            )
        }
        hashes = conn.execute(text("SELECT content_hash FROM artifact_versions")).scalars().all()
    retained = {digest: env[7].open(digest) for digest in hashes}
    unsolicited = counts(env[5], ("audit_findings", "impact_assessments"))
    with env[5].connect() as conn:
        old_sources = conn.execute(
            text("SELECT id,content_hash FROM source_versions ORDER BY id")
        ).all()
    source_transition(env, kind)
    assert counts(env[5], ("audit_findings", "impact_assessments")) == unsolicited
    with env[5].connect() as conn:
        for identity, digest in old_sources:
            assert (
                conn.execute(
                    text("SELECT content_hash FROM source_versions WHERE id=:id"), {"id": identity}
                ).scalar_one()
                == digest
            )
    service, q, aq = queries(env)
    expected = "INVALID" if kind == "RETRACTED" else "STALE"
    for read in (
        lambda: service.get_manuscript_validity(env[3], q),
        lambda: service.get_manuscript_audit(env[3], aq),
    ):
        with sql_protocol(env[5]) as observed:
            current = read()
        assert_snapshot_read(observed, snapshots=1)
        validity: Any = getattr(current, "validity", current)
        assert validity.current_validity == expected
    before = counts(env[5])
    if saved:
        fresh = fresh_publication_service(env)
        with sql_protocol(env[5]) as observed:
            assert fresh.transition_publication_ready(env[2], command) == saved
        assert_snapshot_read(observed, snapshots=1)
        with sql_protocol(env[5]) as observed:
            view = fresh.get_publication_ready_transition(
                env[2], GetPublicationReadyTransitionQuery(command.project_id, saved.id)
            )
        assert_snapshot_read(observed, snapshots=1)
        assert view.consumption == saved and view.current.target_validity == expected
    else:
        with pytest.raises(ResearchBaseError) as denied:
            app.transition_publication_ready(env[2], command)
        assert denied.value.code == ErrorCode.APPROVAL_TARGET_STALE
    if f:
        fresh_package = fresh_package_service(f)
        with sql_protocol(env[5]) as observed:
            current_package = fresh_package.get_prepared_submission(f.actor, f.query)
        assert_snapshot_read(observed, snapshots=1)
        assert current_package.items == package.items
        assert current_package.content_hash == package.content_hash
        assert current_package.current_validity == expected
        if frozen:
            with sql_protocol(env[5]) as observed:
                assert fresh_package.freeze_prepared_submission(f.actor, f.command) == frozen
            assert_snapshot_read(observed, snapshots=1)
            with pytest.raises(ResearchBaseError) as denied:
                fresh_package_service(pending).freeze_prepared_submission(
                    pending.actor, pending.command
                )
            assert denied.value.code == ErrorCode.APPROVAL_TARGET_STALE
        else:
            with pytest.raises(ResearchBaseError) as denied:
                fresh_package.freeze_prepared_submission(f.actor, f.command)
            assert denied.value.code == ErrorCode.APPROVAL_TARGET_STALE
    assert counts(env[5]) == before  # Includes zero unsolicited finding/impact writes.
    with env[5].connect() as conn:
        for table, rows in historical.items():
            assert conn.execute(text(f"SELECT * FROM {table} ORDER BY id")).all() == rows
    assert all(env[7].open(digest) == data for digest, data in retained.items())


@pytest.mark.parametrize("kind", ["CORRECTED", "RETRACTED"])
def test_f1_unrelated_source_control_does_not_block_ready_or_package(b05_env, kind):
    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.b25_support import source_transition

    f = build(b05_env)
    source_transition(b05_env, kind)
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    assert saved.result_prepared_submission_version_id == f.command.result_id
    assert f.app.get_prepared_submission(f.actor, f.query).current_validity == "VALID"
