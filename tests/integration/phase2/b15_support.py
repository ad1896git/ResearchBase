"""B15 accepted B04/S1 fixtures and exact PREPARED Application lifecycle."""

from uuid import uuid4

import pytest

from researchbase.application.authorship import (
    AuthorshipService,
    CreateAuthorshipSnapshotCommand,
    RecordContributionCommand,
)
from researchbase.application.prepared_submission import (
    GetPreparedSubmissionQuery,
    PreparedSubmissionService,
    PrepareSubmissionCommand,
    RecordAuthorConsentCommand,
)
from tests.integration.phase2.test_b04_manuscript_freeze import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b04_manuscript_freeze import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b04_manuscript_freeze import (
    freeze,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

b04_env = _b04_env
conclusion_env = _conclusion_env

pytestmark = pytest.mark.integration


def build_env(b04_env, authors=None):
    b04, q, actor, factory, engine, credentials, store, _, _ = b04_env
    freeze(b04, actor, q)
    s1 = AuthorshipService(factory, credentials)
    authors = authors or (actor.actor_id,)
    contributions = tuple(
        s1.record_contribution(
            actor,
            RecordContributionCommand(
                uuid4(), q.project_id, q.publication_id, author, "WRITING", "Direct authorship"
            ),
        )
        for author in authors
    )
    snapshot = s1.create_authorship_snapshot(
        actor,
        CreateAuthorshipSnapshotCommand(
            uuid4(),
            q.project_id,
            q.publication_id,
            authors,
            (authors[0],),
            (),
            tuple(c.id for c in contributions),
        ),
    )
    service = PreparedSubmissionService(factory, credentials, store)
    command = PrepareSubmissionCommand(
        uuid4(), q.project_id, q.publication_id, q.manuscript_version_id, snapshot.id
    )
    return service, command, actor, factory, engine, store, credentials


def prepared(env):
    service, command, actor, *_ = env
    row = service.prepare_submission(actor, command)
    return row, GetPreparedSubmissionQuery(command.project_id, row.id)


def consent_command(env, package):
    _, command, actor, factory, _, store, _ = env
    evidence = _artifact(factory, store, actor, command.project_id, b"consent evidence")
    return RecordAuthorConsentCommand(
        uuid4(), command.project_id, package, "GRANTED", "PREPARED_PACKAGE", evidence, None
    )


@pytest.fixture
def b15_env(b04_env):
    return build_env(b04_env)
