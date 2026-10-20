"""Deterministic-count disposable benchmark science built only by owning services."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
from researchbase.application.decision import DecisionService, RecordDecisionCommand
from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.publication import PublicationService
from researchbase.application.scientific_conclusion import (
    ClaimInputRequest,
    ScientificConclusionService,
)
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    SourceIdentityService,
    VerifySourceIdentifier,
)
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import (
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.application_compat import LegacyApplicationService
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.test_pr12_application import seed_claim, seed_measurement


def build(m3, url, tmp_path, counts: dict[str, int]) -> dict[str, Any]:
    literature, author, reviewer, project, existing_version, _, document, engine, credentials = m3
    s.upgrade(url)
    factory = literature._factory
    sources = SourceIdentityService(factory, credentials)
    versions = SourceVersionService(factory, credentials)
    identity, _, _ = identity_service(url, credential_verifier=credentials)
    projects = [project] + [
        identity.create_project_with_owner(
            author, name=f"TEST ONLY PR220 project {i}", request_id=uuid4()
        )
        for i in range(1, counts["projects"])
    ]
    with engine.connect() as conn:
        existing_source = conn.execute(
            text("SELECT literature_source_id FROM source_versions WHERE id=:id"),
            {"id": existing_version},
        ).scalar_one()
    source_rows = []
    for index in range(counts["sources"]):
        owner = (
            project
            if index < counts["busy_project_sources"]
            else projects[1 + (index - counts["busy_project_sources"]) % (len(projects) - 1)]
        )
        title = "Technical fixture" if index == 0 else f"TEST ONLY PR220 source {index}"
        doi = f"10.2202/pr220-{index}"
        if index == 0:
            source_id = existing_source
            identifier = sources.add_source_identifier(
                AddSourceIdentifier(
                    author, owner, source_id, IdentifierType.DOI, doi, True, uuid4()
                )
            )
        else:
            identifier = sources.register_literature_source(
                RegisterLiteratureSource(
                    author, owner, SourceKind.PAPER, title, uuid4(), IdentifierType.DOI, doi
                )
            )
            source_id = UUID(str(identifier["source_id"]))
        sources.add_source_identifier(
            AddSourceIdentifier(
                author,
                owner,
                source_id,
                IdentifierType.URL,
                f"https://example.org/pr220/{index}",
                False,
                uuid4(),
            )
        )
        if index < counts["shared_sources"]:
            sources.verify_source_identifier(
                VerifySourceIdentifier(
                    author,
                    owner,
                    UUID(str(identifier["identifier_id"])),
                    UUID(document["artifact_version_id"]),
                    "TEST ONLY shared source identity basis",
                    uuid4(),
                )
            )
            linked = sources.register_literature_source(
                RegisterLiteratureSource(
                    author, projects[1], SourceKind.PAPER, title, uuid4(), IdentifierType.DOI, doi
                )
            )
            assert UUID(str(linked["source_id"])) == source_id
        for version_number in range(1 if index else 2, 3):
            material = SourceVersionMaterial(
                source_id,
                SourceVersionKind.PUBLISHED,
                None,
                None,
                f"{title} version {version_number}",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            )
            created = versions.create(CreateSourceVersion(author, owner, material, uuid4()))
            versions.freeze(
                TransitionSourceVersion(
                    author, owner, UUID(str(created["source_version_id"])), uuid4()
                )
            )
        source_rows.append((owner, source_id, doi))
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "pr220-cas")
    app = LegacyApplicationService(factory, SystemClock(), store)
    execution = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    measurements = [
        seed_measurement(app, ProjectId(project), execution, f"pr220-m{i}") for i in range(4)
    ]
    claims = []
    for _ in range(counts["claims"]):
        claim, draft = seed_claim(app, ProjectId(project), execution)
        for measurement in measurements:
            current = app.get_current_claim_version(claim.id)
            app.link_evidence(
                LinkEvidenceCommand(
                    claim.id,
                    draft.id,
                    measurement,
                    None,
                    "supports",
                    None,
                    current.row_version,
                    execution,
                )
            )
        current = app.get_current_claim_version(claim.id)
        frozen = app.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, draft.id, execution, current.row_version)
        )
        claims.append(UUID(str(frozen.id)))
    publications = PublicationService(factory, credentials, store)
    artifact = _artifact(
        factory, store, author, project, b"TEST ONLY PR220 manuscript", "manuscript"
    )
    manuscripts = []
    for index in range(counts["manuscripts"]):
        publication = publications.create_publication(
            author, project, "PAPER", f"TEST ONLY paper {index}", uuid4()
        )
        draft = publications.create_draft(
            author, project, publication.id, artifact, "TEST ONLY paper", None, "INITIAL", uuid4()
        )
        manuscripts.append((publication.id, draft.id))
        size = counts["high_placements"] if index == 1 else counts["typical_placements"]
        for ordinal in range(size):
            ClaimPlacementService(factory, credentials).add(
                author,
                project,
                publication.id,
                draft.id,
                claims[ordinal % len(claims)],
                None,
                "RESULTS",
                {"kind": "PARAGRAPH", "value": f"p{ordinal}"},
                "DESCRIPTIVE",
                ordinal,
                uuid4(),
            )
    conclusions = ScientificConclusionService(factory, credentials, literature)
    reviews = InternalReviewService(factory, credentials, literature)
    targets = []
    per_target = counts["reviews"] // counts["conclusion_targets"]
    per_review = counts["issues"] // counts["reviews"]
    for index in range(counts["conclusion_targets"]):
        created = conclusions.create(
            author,
            project,
            f"TEST ONLY conclusion {index}",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(claims[index % len(claims)], "SUPPORTS"),),
            (),
            uuid4(),
        )
        conclusions.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
        for _ in range(per_target):
            reviews.create(
                reviewer,
                project,
                "SCIENTIFIC_CONCLUSION_VERSION",
                created.version_id,
                "SCIENTIFIC",
                "ACCEPT",
                "TEST ONLY complete independent review",
                tuple(
                    ReviewIssueRequest("INFO", "OTHER", f"TEST ONLY issue {i}")
                    for i in range(per_review)
                ),
                uuid4(),
            )
        targets.append(created.version_id)
    tables = {
        "projects": "projects",
        "sources": "literature_sources",
        "source_versions": "source_versions",
        "identifiers": "source_identifiers",
        "project_links": "literature_source_project_links",
        "claims": "claim_versions",
        "manuscripts": "manuscript_versions",
        "conclusion_targets": "scientific_conclusion_versions",
        "reviews": "internal_review_records",
        "issues": "review_issues",
    }
    actual = dict(counts)
    with engine.connect() as conn:
        for key, table in tables.items():
            actual[key] = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        assert (
            conn.execute(
                text("SELECT count(*) FROM source_versions WHERE status IN ('FROZEN','SUPERSEDED')")
            ).scalar_one()
            == counts["source_versions"]
        )
        assert (
            conn.execute(text("SELECT count(*) FROM evidence_relations")).scalar_one()
            == counts["claims"] * 4
        )
        distribution = (
            conn.execute(
                text(
                    "SELECT count(*) FROM literature_source_project_links GROUP BY lite"
                    "rature_source_id"
                )
            )
            .scalars()
            .all()
        )
        assert distribution.count(2) == counts["shared_sources"]
        assert max(distribution) == 2
        assert (
            conn.execute(
                text("SELECT count(*) FROM literature_source_project_links WHERE project_id=:id"),
                {"id": project},
            ).scalar_one()
            == counts["busy_project_sources"]
        )
    assert actual == counts
    with engine.begin() as conn:
        conn.execute(text("ANALYZE"))
    canonical = s.manifest(
        engine,
        tuple(tables.values()) + ("evidence_relations", "scientific_conclusion_claim_inputs"),
    )
    canonical = s.persist_manifest("benchmark-fixture", canonical)
    s.save_observation(
        "benchmark-fixture",
        {
            "actual_counts": actual,
            "manifest": canonical,
            "limitation": "Superseded manuscript history BLOCKED: owning lifecycle unavailable",
        },
    )
    decisions = DecisionService(factory, credentials, literature)
    commands = [
        RecordDecisionCommand(uuid4(), project, target, "q" * 128, "r" * 128) for target in targets
    ]
    s.save_observation(
        "benchmark-request-identities",
        {
            "requests": [
                {
                    "request_id": str(command.id),
                    "target_version_id": str(command.scientific_conclusion_version_id),
                }
                for command in commands
            ]
        },
    )
    saved = {}
    trace = ManuscriptScientificTraceService(factory, credentials)
    expected_traces = [trace.trace(author, project, *pair) for pair in manuscripts[:2]]

    def prepare(case):
        if case == "decision-replay":
            for i, request in enumerate(commands):
                saved[i] = decisions.record_decision(reviewer, request)

    def call(case, index):
        if case.startswith("lookup"):
            caller = replace(author, actor_id=uuid4()) if case == "lookup-denied" else author
            identifier = "10.2202/pr220-0" if case != "lookup-miss" else "10.2202/absent"
            try:
                result = sources.find_source_by_identifier(
                    caller, project, IdentifierType.DOI, identifier
                )
            except ResearchBaseError as error:
                assert error.code == (
                    ErrorCode.AUTHENTICATION_REQUIRED
                    if case == "lookup-denied"
                    else ErrorCode.SOURCE_NOT_FOUND
                )
                return error.code.value
            assert case == "lookup-hit" and UUID(str(result["source_id"])) == existing_source
            return result
        if case.startswith("trace"):
            position = 1 if case == "trace-high" else 0
            result = trace.trace(author, project, *manuscripts[position])
            assert result == expected_traces[position]
            return result
        if case in {"decision-first-write", "review-gate"}:
            assert index not in saved, "first-write must have a fresh exact target/request"
            result = decisions.record_decision(reviewer, commands[index])
            assert (
                len([ref for ref in result.basis if ref.type == "InternalReviewRecord"])
                == per_target
            )
            saved[index] = result
            return result
        assert case == "decision-replay" and index in saved
        result = decisions.record_decision(reviewer, commands[index])
        assert result == saved[index]
        return result

    return {
        "counts": actual,
        "call": call,
        "prepare": prepare,
        "limitation": "Superseded manuscript history BLOCKED: owning lifecycle unavailable",
    }


def build_b29(decision_env):
    """Legal mostly-OPEN/selectivity fixture; identity shared by physical clones.

    Distribution is deterministic; owning services allocate and persist the exact
    UUIDs subsequently copied into both databases. No direct scientific writes.
    """
    from researchbase.application.decision import RecordRevisionDecisionCommand
    from researchbase.application.internal_review import RecordIssueDispositionCommand
    from researchbase.application.revision_action import (
        RecordConcernReReviewCommand,
        RecordRevisionActionCommand,
        RevisionActionService,
    )

    decisions, reviews, actor, _, base = decision_env
    scientific, _, literature, author, _, project, claim, _, engine, credentials = base
    revisions = RevisionActionService(base[1], credentials, literature)

    def target(label):
        item = scientific.create(
            author,
            project,
            f"TEST ONLY B29 {label}",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(claim, "SUPPORTS"),),
            (),
            uuid4(),
        )
        scientific.freeze(author, project, item.conclusion_id, item.version_id, uuid4())
        return item.version_id

    targets = {name: target(name) for name in ("sparse", "dense", "miss", "terminal")}

    def review(exact, issues=()):
        return reviews.create(
            actor,
            project,
            "SCIENTIFIC_CONCLUSION_VERSION",
            exact,
            "SCIENTIFIC",
            "ACCEPT",
            "TEST ONLY B29 complete review",
            issues,
            uuid4(),
        )

    for kind in ("sparse", "dense", "miss"):
        # 25 zero-Issue favorable reviews plus 24 populated reviews per target.
        for _ in range(25):
            review(targets[kind])
        for number in range(24):
            review(
                targets[kind],
                tuple(
                    ReviewIssueRequest(
                        "BLOCKING"
                        if kind == "dense" or (kind == "sparse" and number == i == 0)
                        else "INFO",
                        "OTHER",
                        f"TEST ONLY B29 Issue {i}",
                    )
                    for i in range(32)
                ),
            )
    # A second target class for measured cardinalities; zero-Issue reviews count.
    reviews.create(
        actor,
        project,
        "CLAIM_VERSION",
        claim,
        "SCIENTIFIC",
        "ACCEPT",
        "TEST ONLY B29 Claim review",
        (),
        uuid4(),
    )
    cost_targets = [target(f"cost-{i}") for i in range(13)]
    pending = []
    for index in range(14):
        exact = targets["terminal"] if index == 0 else cost_targets[index - 1]
        old = review(exact, (ReviewIssueRequest("BLOCKING", "OTHER", "TEST ONLY concern"),))
        decision = decisions.record_revision_decision(
            actor,
            RecordRevisionDecisionCommand(
                uuid4(),
                project,
                old.issues[0].id,
                "Dismiss concern?",
                "Exact basis",
                "ACCEPT_NO_CHANGE",
            ),
        )
        action = revisions.record_revision_action(
            author,
            RecordRevisionActionCommand(
                uuid4(), project, "NO_CHANGE", decision_record_id=decision.id
            ),
        )
        rereview = review(exact)
        revisions.record_concern_re_review(
            actor, RecordConcernReReviewCommand(project, action.id, rereview.id)
        )
        command = RecordIssueDispositionCommand(
            uuid4(),
            project,
            old.issues[0].id,
            "DISMISSED",
            action.id,
            rereview.id,
            "I attest the exact no-change response resolves this concern",
            decision.id,
        )
        if index == 0:
            reviews.record_issue_disposition(actor, command)
            terminal_issue = command.review_issue_id
        else:
            pending.append(command)
    replay = RecordDecisionCommand(uuid4(), project, targets["miss"], "Proceed?", "Complete basis")
    saved = decisions.record_decision(actor, replay)
    assert len([ref for ref in saved.basis if ref.type == "InternalReviewRecord"]) == 49
    denied = RecordDecisionCommand(
        uuid4(), project, targets["sparse"], "Proceed?", "Complete basis"
    )
    try:
        decisions.record_decision(actor, denied)
    except ResearchBaseError as error:
        denial_code = error.code.value
    else:
        raise AssertionError("single blocker was filtered")
    with engine.begin() as conn:
        conn.execute(text("ANALYZE"))
    return dict(
        terminal_issue=terminal_issue,
        base=base,
        actor=actor,
        **targets,
        dispositions=pending,
        insert_ids=[uuid4() for _ in range(13)],
        insert_targets=cost_targets,
        replay=replay,
        denied=denied,
        denial_code=denial_code,
    )


APPROVAL_CASES = (
    "request-first",
    "request-replay",
    "decision-first",
    "decision-replay",
    "request-denied",
    "decision-denied",
    "same-target-replay",
)


def approval_profile(env, case, count):
    """Allocate legal independent targets outside timing; preserve service retry rules."""
    from researchbase.application.approval import RequestApprovalCommand
    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_approval import _decide

    approval, requester, approver, template, decision_env = env
    base = decision_env[-1]
    scientific, _, _, _, _, project, claim, *_ = base
    author = requester
    identity, _, _ = identity_service(base[8].url.render_as_string(hide_password=False))
    app = LegacyApplicationService(base[1], SystemClock(), base[2]._store)
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    commands, decisions, expected = [], [], []
    for index in range(1 if case == "same-target-replay" else count):
        # Selection is scoped by project/purpose, not target. Independent targets
        # therefore need distinct projects; otherwise preparing a later request
        # intentionally makes earlier requests stale before timing starts.
        project = identity.create_project_with_owner(
            author, name=f"TEST ONLY H2 scope {index}", request_id=uuid4()
        )
        for principal, role in (
            (decision_env[2], "OWNER"),
            (requester, "RESEARCHER"),
            (approver, "APPROVER"),
        ):
            identity.assign_project_role(
                AssignProjectRole(
                    author,
                    project,
                    principal.actor_id,
                    role,
                    "Independent H2 benchmark scope",
                    uuid4(),
                )
            )
        measurement = seed_measurement(app, ProjectId(project), context, f"h2-{index}")
        parent, draft = seed_claim(app, ProjectId(project), context)
        app.link_evidence(
            LinkEvidenceCommand(
                parent.id, draft.id, measurement, None, "supports", None, draft.row_version, context
            )
        )
        linked = app.get_current_claim_version(parent.id)
        claim = app.freeze_claim_version(
            FreezeClaimVersionCommand(parent.id, linked.id, context, linked.row_version)
        ).id
        target = scientific.create(
            author,
            project,
            f"TEST ONLY H2 approval {index}",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(claim, "SUPPORTS"),),
            (),
            uuid4(),
        )
        scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
        review = decision_env[1].create(
            decision_env[2],
            project,
            "SCIENTIFIC_CONCLUSION_VERSION",
            target.version_id,
            "SCIENTIFIC",
            "ACCEPT",
            "Independent H2 review",
            (),
            uuid4(),
        )
        basis = decision_env[0].record_decision(
            decision_env[2],
            RecordDecisionCommand(
                uuid4(), project, target.version_id, "Release?", "Independent H2 basis"
            ),
        )
        request = RequestApprovalCommand(
            uuid4(), project, target.version_id, basis.id, (review.id,)
        )
        command = _decide(request)
        saved = None
        if case not in {"request-first", "request-denied"}:
            saved = approval.request_approval(requester, request)
        if case == "decision-replay" or case.startswith("consume"):
            saved = approval.decide_approval(approver, command)
        commands.append(request)
        decisions.append(command)
        expected.append(saved)
        if case.startswith("consume"):
            from researchbase.application.approval import RecordInternalScientificReleaseCommand

            assert saved is not None and saved.grant is not None
            consumption = RecordInternalScientificReleaseCommand(
                uuid4(), project, saved.grant.id, target.version_id, request.review_ids
            )
            decisions[-1] = consumption
            if case != "consume-first":
                expected[-1] = scientific.record_internal_scientific_release(requester, consumption)

    def call(index):
        slot = 0 if case == "same-target-replay" else index
        request = commands[slot]
        try:
            if case == "consume-read":
                result = approval.get_grant_consumption(
                    requester, request.project_id, decisions[slot].command_key
                )
            elif case.startswith("consume"):
                result = scientific.record_internal_scientific_release(requester, decisions[slot])
            elif case == "request-denied":
                result = approval.request_approval(decision_env[2], request)
            elif case == "decision-denied":
                result = approval.decide_approval(requester, decisions[slot])
            elif case.startswith("decision"):
                result = approval.decide_approval(approver, decisions[slot])
            else:
                result = approval.request_approval(requester, request)
        except ResearchBaseError as error:
            assert case.endswith("denied")
            assert error.code == (
                ErrorCode.CONFLICT_OF_INTEREST if case == "request-denied" else ErrorCode.FORBIDDEN
            )
            return error.code.value
        assert not case.endswith("denied")
        if case.endswith("replay") or case == "consume-read":
            assert result == expected[slot]
        return result

    return call


def revision_profile(env, kind, count):
    """Independent concerns; every scientific result comes from the owning fixture."""
    from tests.integration.phase2.b08_support import disposition_case
    from tests.integration.phase2.test_b07_concurrency import prepared

    revisions, template, decisions, _, revised = env
    base = decisions[-1]
    operations = []
    for _ in range(count):
        review = decisions[1].create(
            decisions[2],
            base[5],
            "SCIENTIFIC_CONCLUSION_VERSION",
            decisions[3].version_id,
            "SCIENTIFIC",
            "MAJOR_REVISION",
            "Independent benchmark concern",
            (ReviewIssueRequest("BLOCKING", "OTHER", "Exact response required"),),
            uuid4(),
        )
        action = replace(template, id=uuid4(), review_issue_id=review.issues[0].id)
        local = revisions, action, decisions, review, revised
        if kind == "disposition":
            app, actor, command, _, _ = disposition_case(local)

            def write(app=app, actor=actor, command=command):
                return app.record_issue_disposition(actor, command)

            def read(app=app, actor=actor, command=command):
                return app.get_issue_disposition(actor, command.project_id, command.id)
        else:
            operations.append(prepared(local, kind))
            continue
        operations.append((write, read))
    return operations


def publication_profile_env(env):
    """Independent project/purpose scope, initial manuscript only (no M1 history)."""
    from researchbase.application.manuscript_freeze import GetManuscriptVersionQuery
    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_approval import _actor

    # The owning reviewer fixture is in test-deployment; the source author is in
    # another deployment. Reuse its existing bound-actor helper, never relabel a binding.
    reviewer = env[3]
    actor = _actor((None, None, reviewer, env[10]))
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    project = identity.create_project_with_owner(
        actor, name="S3 independent publication scope", request_id=uuid4()
    )
    identity.assign_project_role(
        AssignProjectRole(actor, project, reviewer.actor_id, "OWNER", "Independent review", uuid4())
    )
    app = PublicationService(env[4], env[9], env[7])
    document = _artifact(env[4], env[7], actor, project, b"S3 initial manuscript", "manuscript")
    publication = app.create_publication(actor, project, "PAPER", "S3 study", uuid4())
    draft = app.create_draft(
        actor, project, publication.id, document, "S3 study", None, "INITIAL", uuid4()
    )
    query = GetManuscriptVersionQuery(project, publication.id, draft.id)
    return (env[0], query, actor, *env[3:])


def novelty_profile(e, case, count):
    """B19 exact positive basis and B22 append-only chains, never a novelty gate."""
    from researchbase.application.novelty import ExactReadQuery, PriorArtSelectionQuery
    from researchbase.domain.novelty import (
        ClosenessCriteria,
        NoveltyOutcome,
        PriorArtBasisInput,
        PriorArtKind,
    )

    operations = []
    for _ in range(count):
        root_command = replace(
            e["commands"]["prior_art"], id=uuid4(), relation=PriorArtKind.IDENTICAL
        )
        root = e["service"].record_prior_art_relation(e["author"], root_command)
        if case == "close":
            command = replace(
                e["commands"]["novelty"],
                id=uuid4(),
                assessment=NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
                prior_art_basis=(PriorArtBasisInput(root.id, e["resolution"]["command"].id),),
                scope_statement="Inspected selected executions",
                closeness_criteria=ClosenessCriteria(("Same method", "Same result")),
            )

            def write_close(command=command):
                return e["service"].record_novelty_assessment(e["author"], command)

            def read_close(command=command):
                return e["service"].read_novelty_assessment(
                    e["author"], ExactReadQuery(e["project"], command.id)
                )

            operations.append((write_close, read_close))
        elif case == "correction":
            command = replace(root_command, id=uuid4(), supersedes_prior_art_relation_id=root.id)

            def write_correction(command=command):
                return e["service"].record_prior_art_relation(e["author"], command)

            def read_correction(command=command):
                return e["service"].read_prior_art_relation(
                    e["author"], ExactReadQuery(e["project"], command.id)
                )

            operations.append((write_correction, read_correction))
        else:

            def read_selection():
                return e["service"].select_prior_art_relation(
                    e["author"], PriorArtSelectionQuery(e["project"], e["claim"], e["source"])
                )

            operations.append((read_selection, read_selection))
    return operations
