"""Fake consumption uses durable gates; no provider or reserved execution activation."""

import pytest
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.test_pr3_04_accounting import setup
from tests.integration.phase3.test_pr3_04_application import bind, reserve

from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def test_restart_reconstructs_unknown_reservation(planning):
    p = planning
    task, fake = setup(p)
    fake.execute(p.principal, reserve(p, task, 4))
    restarted = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    assert restarted.reconstruct(p.principal, p.project, task).parallel_branches == 1
    with pytest.raises(ResearchBaseError):
        restarted.execute(p.principal, reserve(p, task, 5))
    with pytest.raises(ResearchBaseError) as exc:
        p.service.execute(p.principal, p.command("start_research_task", task, 5))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def test_missing_gate_never_dispatches(planning):
    p = planning
    task = p.create()
    bind(p, task)
    fake = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    with pytest.raises(ResearchBaseError):
        fake.execute(p.principal, reserve(p, task, 2))
    assert fake.reconstruct(p.principal, p.project, task).reserved.llm_calls == 0
