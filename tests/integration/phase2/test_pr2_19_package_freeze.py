"""G7 package suffix, separate from remaining novelty and full Phase 2 gates."""

from dataclasses import replace

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
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
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
    assert current.content_hash == package.content_hash and current.items == package.items
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
