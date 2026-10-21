"""Frozen current-authority disclosure boundary; committed admissions survive denial."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    RecoverLiteratureSearchExecution,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.unit.phase2.test_pr2_04_transport_coverage import (
    _Authority,
    _body,
    _Credential,
    _transport,
)


@pytest.mark.parametrize("action", ["execute", "cancel", "recover"])
@pytest.mark.parametrize("loss", ["role", "credential"])
@pytest.mark.parametrize("lock_retry", [False, True], ids=["direct", "after-lock-retry"])
@pytest.mark.pr204_requirements("PR204-AUTH-03", "PR204-IDEM-06")
def test_disclosure_denial_preserves_committed_facts_without_replaying_work(
    action, loss, lock_retry, monkeypatch, pr204_trace: FactRecorder
):
    client, _, repo, provider, services = _transport()
    body = _body()
    created = client.post(
        "/literature/search-executions", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert created.status_code == 201
    execution_id = UUID(created.json()["execution_id"])
    principal = services.verified_principal
    service = services.literature_search_executions
    if action == "recover":
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=UUID(body["project_id"]),
                principal=principal,
            )
        )
    armed = False
    saved = None
    calls = None
    stages = []
    orchestration_count = 0
    lock_count = 0
    original_authorize = _Authority.authorize
    original_get = repo.get_for_update

    def lock(self, project):
        nonlocal lock_count
        if armed:
            lock_count += 1
            stages.append("project_lock")
            if lock_retry and lock_count == 1:
                raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "test lock retry")

    def reread(identity):
        if armed:
            stages.append("locked_execution_reread")
        return original_get(identity)

    def authority(self, supplied, project):
        if armed:
            stages.append("authority_reread")
        return [] if armed and loss == "role" else original_authorize(self, supplied, project)

    def clock(self):
        now = datetime.now(UTC)
        if armed:
            stages.append("fresh_clock")
            pr204_trace.record(disclosure_database_time=now, lock_attempt=lock_count)
        return now

    def credential(self, supplied, at):
        if armed:
            stages.append("credential_check")
        return not (armed and loss == "credential")

    boundary = {"execute": "_drive", "cancel": "_finalize_cancel", "recover": "_cancel_or_recover"}[
        action
    ]
    original_boundary = getattr(service, boundary)

    def lose_after_commit(*args, **kwargs):
        nonlocal armed, saved, calls, orchestration_count
        result = original_boundary(*args, **kwargs)
        orchestration_count += 1
        saved = deepcopy(vars(repo))
        calls = len(provider.calls)
        armed = True
        return result

    monkeypatch.setattr(_Authority, "lock_project", lock)
    monkeypatch.setattr(repo, "get_for_update", reread)
    monkeypatch.setattr(_Authority, "authorize", authority)
    monkeypatch.setattr(_Authority, "at", clock)
    monkeypatch.setattr(_Credential, "is_valid", credential)
    monkeypatch.setattr(service, boundary, lose_after_commit)
    command_type = {
        "execute": ExecuteLiteratureSearchExecution,
        "cancel": CancelLiteratureSearchExecution,
        "recover": RecoverLiteratureSearchExecution,
    }[action]
    command = command_type(
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=UUID(body["project_id"]),
        principal=principal,
    )
    with pytest.raises(ResearchBaseError) as denied:
        getattr(service, action)(command)
    pr204_trace.record(
        action=action,
        loss=loss,
        lock_retry=lock_retry,
        error=denied.value.code.value,
        stages=stages,
        saved=repr(saved),
        after=repr(vars(repo)),
        provider_calls=len(provider.calls),
        orchestration_count=orchestration_count,
    )
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert vars(repo) == saved and len(provider.calls) == calls
    assert orchestration_count == 1
    assert lock_count == (2 if lock_retry else 1)
    assert stages[-5:] == [
        "project_lock",
        "locked_execution_reread",
        "authority_reread",
        "fresh_clock",
        "credential_check",
    ]
    assert len(repo.receipts) == (3 if action == "recover" else 2)
