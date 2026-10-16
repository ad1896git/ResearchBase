"""Shared PostgreSQL builders for revision and disposition verification."""

from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import text


@contextmanager
def normal_role(engine):
    role = "b07_normal_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
        )
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        yield conn
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.execute(text("RESET ROLE"))
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE {role}"))


def _claim_with_result(base, *, measurement=None, statistic=None):
    from researchbase.application.commands import (
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        ReviseClaimCommand,
    )
    from researchbase.domain.claim import ClaimVersionId
    from tests.integration.phase2.test_b06_revision_action import _app, _context

    app = _app(base)
    old = app.get_claim_version(ClaimVersionId(base[6]))
    parent = app.get_claim(old.claim_id)
    app.revise_claim(
        ReviseClaimCommand(
            parent.id, "Exact completed result", {}, None, parent.row_version, _context(base)
        )
    )
    draft = app.get_current_claim_version(parent.id)
    app.link_evidence(
        LinkEvidenceCommand(
            parent.id,
            draft.id,
            measurement,
            statistic,
            "supports",
            None,
            draft.row_version,
            _context(base),
        )
    )
    draft = app.get_current_claim_version(parent.id)
    return app.freeze_claim_version(
        FreezeClaimVersionCommand(parent.id, draft.id, _context(base), draft.row_version)
    ).id
