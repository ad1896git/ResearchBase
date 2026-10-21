"""G7 package suffix, separate from remaining novelty and full Phase 2 gates."""

from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import inspect

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import pr2_19_support as g
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    counts,
    decision_env,
    phase2_database_url,
    revision_env,
    withdraw_consent,
)
from tests.integration.phase2.pr2_19_support import prepared_package_trace

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytestmark = pytest.mark.integration


def test_g7_ready_preparation_consent_freeze_then_withdrawal_is_derived_stale(b17_env):
    f = b17_env
    before = counts(f)
    receipt, package = prepared_package_trace(f)
    after = counts(f)
    tables = (
        "prepared_submission_versions",
        "prepared_submission_manifest_items",
        "prepared_submission_events",
        "approval_grant_consumptions",
        "approval_grant_events",
        "author_consents",
    )
    g.emit_observation(
        g.ScenarioObservation(
            "G7",
            0,
            "PreparedSubmissionService.freeze_prepared_submission",
            (receipt.id, package.id),
            None,
            tuple(g.StateDelta(t, b, a) for t, b, a in zip(tables, before, after, strict=True)),
            (
                g.VerifiedHash(
                    package.id,
                    "package_manifest_hash",
                    f.command.expected_package_manifest_hash,
                    package.package_manifest_hash,
                ),
            ),
            (),
            (),
            (),
        )
    )
    withdraw_consent(f)
    current = f.app.get_prepared_submission(f.actor, f.query)
    assert current.status == "FROZEN" and current.current_validity == "STALE"
    assert (
        current.content_hash,
        current.package_manifest_hash,
        current.frozen_at,
        current.items,
        current.events,
    ) == (
        package.content_hash,
        package.package_manifest_hash,
        package.frozen_at,
        package.items,
        package.events,
    )
    assert f.app.freeze_prepared_submission(f.actor, f.command) == receipt
    assert not {"submission_records", "submission_versions", "external_effects"} & set(
        inspect(f.engine).get_table_names()
    )


def test_g7_denied_freeze_has_no_partial_suffix(b17_env):
    f = b17_env
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(
            f.actor, replace(f.command, expected_package_manifest_hash="f" * 64)
        )
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert counts(f) == before


def test_g7_full_committed_trace_literal_hashes_and_snapshot_readers(b05_env, monkeypatch):
    import hashlib
    import json

    from researchbase.application.approval import ApprovalService
    from researchbase.application.decision import DecisionService
    from researchbase.application.prepared_submission import (
        GetAuthorConsentQuery,
        PreparedSubmissionService,
    )
    from researchbase.application.publication import (
        GetPublicationReadyTransitionQuery,
        PublicationService,
    )
    from researchbase.persistence.approval_repository import (
        B09_DECIDE_SHARE_SQL,
        B09_SHARE_SQL,
        B13_SHARE_SQL,
    )
    from researchbase.persistence.decision_repository import B11_SHARE_SQL
    from researchbase.persistence.prepared_submission_repository import (
        B15_SHARE_SQL,
        B16_SHARE_SQL,
        B17_SHARE_SQL,
    )
    from researchbase.persistence.publication_repository import B14A_SHARE_SQL
    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.b30_observations import (
        assert_first_share,
        assert_snapshot_read,
        sql_protocol,
    )

    env = b05_env
    trace = []
    for cls, name, inventory in (
        (PublicationService, "transition_publication_internal_review", B14A_SHARE_SQL),
        (DecisionService, "record_ready_for_submission_decision", B11_SHARE_SQL),
        (DecisionService, "record_prepare_submission_decision", B11_SHARE_SQL),
        (ApprovalService, "request_approval", B09_SHARE_SQL),
        (ApprovalService, "decide_approval", B09_DECIDE_SHARE_SQL),
        (PublicationService, "transition_publication_ready", B13_SHARE_SQL),
        (PreparedSubmissionService, "prepare_submission", B15_SHARE_SQL),
        (PreparedSubmissionService, "record_author_consent", B16_SHARE_SQL),
        (PreparedSubmissionService, "freeze_prepared_submission", B17_SHARE_SQL),
    ):
        assert (
            inventory
            == g.S2_FIRST_SHARE[
                {
                    "transition_publication_internal_review": "B14A_SHARE_SQL",
                    "record_ready_for_submission_decision": "B11_SHARE_SQL",
                    "record_prepare_submission_decision": "B11_SHARE_SQL",
                    "request_approval": "B09_SHARE_SQL",
                    "decide_approval": "B09_DECIDE_SHARE_SQL",
                    "transition_publication_ready": "B13_SHARE_SQL",
                    "prepare_submission": "B15_SHARE_SQL",
                    "record_author_consent": "B16_SHARE_SQL",
                    "freeze_prepared_submission": "B17_SHARE_SQL",
                }[name]
            ]
        )
        original = getattr(cls, name)

        def wrap(original=original, name=name, inventory=inventory, cls=cls):
            def observed(self, *args, **kwargs):
                before = g.counts(env[5])
                with sql_protocol(env[5]) as statements:
                    result = original(self, *args, **kwargs)
                isolation = (
                    "SERIALIZABLE"
                    if name in {"transition_publication_ready", "freeze_prepared_submission"}
                    else "READ_COMMITTED"
                )
                assert_first_share(statements, inventory, isolation)
                if name in {"transition_publication_ready", "freeze_prepared_submission"}:
                    g.assert_s2_consumption_protocol(
                        statements, args[1], package=name == "freeze_prepared_submission"
                    )
                after = g.counts(env[5])
                identity = getattr(result, "id", None)
                g.emit_observation(
                    g.ScenarioObservation(
                        "G7",
                        len(trace),
                        cls.__name__ + "." + name,
                        (identity,) if identity else (),
                        None,
                        tuple(g.StateDelta(table, before[table], after[table]) for table in before),
                        (),
                        tuple(t.backend_pid for t in statements.transactions),
                        (),
                        (),
                    )
                )
                trace.append((name, result))
                return result

            return observed

        monkeypatch.setattr(cls, name, wrap())
    f: Any = build(env)
    receipt, package = prepared_package_trace(f)
    assert [name for name, _ in trace].count("decide_approval") == 2
    assert f.ready_command.grant_id != f.command.grant_id
    assert trace[-1][0] == "freeze_prepared_submission"

    def digest(material):
        return hashlib.sha256(
            json.dumps(
                material, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode()
        ).hexdigest()

    def ref(kind, identity, value):
        return {"type": kind, "id": str(identity), "content_hash": value}

    from sqlalchemy import text

    with env[5].connect() as conn:
        manuscript_hash = conn.execute(
            text("SELECT content_hash FROM manuscript_versions WHERE id=:id"),
            {"id": package.manuscript_version_id},
        ).scalar_one()
        authorship_hash = conn.execute(
            text("SELECT content_hash FROM authorship_snapshots WHERE id=:id"),
            {"id": package.authorship_snapshot_id},
        ).scalar_one()
    manuscript = ref("ManuscriptVersion", package.manuscript_version_id, manuscript_hash)
    authorship = ref("AuthorshipSnapshot", package.authorship_snapshot_id, authorship_hash)
    consent = ref("AuthorConsent", f.consent.id, f.consent.content_hash)
    # This graph deliberately has no scientific placements: one exact consent occurrence.
    assert [(i.category, i.ordinal, i.target.id) for i in package.items] == [
        ("AUTHOR_CONSENT", 0, f.consent.id)
    ]
    manifest = digest(
        {
            "type": "PreparedSubmissionVersionManifest",
            "material_version": 1,
            "manuscript_version": manuscript,
            "authorship_snapshot": authorship,
            "items": [{"category": "AUTHOR_CONSENT", "ordinal": 0, "target": consent}],
        }
    )
    assert package.package_manifest_hash == manifest
    assert package.content_hash == digest(
        {
            "type": "PreparedSubmissionVersion",
            "material_version": 1,
            "publication_id": str(package.publication_id),
            "manuscript_version": manuscript,
            "authorship_snapshot": authorship,
            "package_manifest_hash": manifest,
        }
    )
    assert f.consent.content_hash == digest(
        {
            "type": "AuthorConsent",
            "material_version": 1,
            "prepared_submission": {"type": "PreparedSubmissionVersion", "id": str(package.id)},
            "actor": {"type": "ActorIdentity", "id": str(f.actor.actor_id)},
            "consent_state": "GRANTED",
            "consent_scope": "PREPARED_PACKAGE",
            "evidence_artifact": ref(
                "ArtifactVersion",
                f.consent.evidence_artifact.id,
                f.consent.evidence_artifact.content_hash,
            ),
            "prior_consent": None,
        }
    )
    # Restore writers so completed replay is observed independently of write wrappers.
    monkeypatch.undo()
    app = g.fresh_package_service(f)
    publication = g.fresh_publication_service(env)
    approval = ApprovalService(env[4], env[9], env[10][2])
    ready_receipt = approval.get_grant_consumption(
        f.actor, f.command.project_id, f.ready_command.command_key
    )
    readers = (
        lambda: app.get_prepared_submission(f.actor, f.query),
        lambda: app.get_prepared_submission_history(f.actor, f.query),
        lambda: app.preview_prepared_submission(f.actor, f.query),
        lambda: app.freeze_prepared_submission(f.actor, f.command),
        lambda: publication.transition_publication_ready(f.actor, f.ready_command),
        lambda: publication.get_publication_ready_transition(
            f.actor, GetPublicationReadyTransitionQuery(f.command.project_id, ready_receipt.id)
        ),
        lambda: approval.get_grant_consumption(
            f.actor, f.command.project_id, f.command.command_key
        ),
        lambda: app.get_author_consent(
            f.actor, GetAuthorConsentQuery(f.command.project_id, f.consent.id)
        ),
    )
    for read in readers:
        with sql_protocol(env[5]) as statements:
            assert read() is not None
        assert_snapshot_read(statements, snapshots=1)
    assert receipt.result_prepared_submission_version_id == package.id
    assert ready_receipt.result_publication_id == package.publication_id
    assert (
        approval.get_grant(f.actor, f.command.project_id, receipt.grant_id).target_content_hash
        == manuscript_hash
    )
