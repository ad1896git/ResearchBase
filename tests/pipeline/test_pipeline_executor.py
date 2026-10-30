"""Publication adapter negatives; real SIGKILL acceptance is a separate opt-in rehearsal."""

import json
from dataclasses import asdict, replace

import pytest
from scripts import pipeline_executor as executor
from scripts.pipeline_protocol import ProtocolError, StateStore

A, B = "a" * 40, "b" * 40


@pytest.fixture
def setup(tmp_path, monkeypatch):
    target = executor.Target("test/sandbox", "main", "pipeline-test/recovery", str(tmp_path), A, B)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"

    class Remote:
        branch = None
        rows = []
        creates = 0
        pushes = 0
        fail_create = False

        def __init__(self, target):
            self.target = target

        def branch_head(self, branch):
            return B if branch == "main" else self.branch

        def prs(self):
            return self.rows

        validate_pr = executor.GitHub.validate_pr

        def push(self):
            type(self).pushes += 1
            type(self).branch = A

        def create(self):
            type(self).creates += 1
            if self.fail_create:
                raise RuntimeError("network outcome unknown")
            type(self).rows = [
                dict(
                    number=17,
                    headRefName=self.target.branch,
                    headRefOid=A,
                    baseRefName="main",
                    baseRefOid=B,
                    isDraft=True,
                    state="OPEN",
                    headRepository={"nameWithOwner": "test/sandbox"},
                )
            ]

    monkeypatch.setattr(executor, "GitHub", Remote)
    monkeypatch.setattr(executor, "run", lambda *args, **kw: A if args[1] == "rev-parse" else "")
    return target, control, evidence, Remote


def test_restart_queries_existing_pr_and_does_not_create_again(setup):
    target, control, evidence, remote = setup
    result = executor.publish(target, control, evidence, initialize=True)
    assert result.pr == 17
    assert executor.publish(target, control, evidence) == result
    assert (remote.pushes, remote.creates) == (1, 1)
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 1


@pytest.mark.parametrize("point", ["after-push", "after-pr"])
def test_interrupted_publication_uses_original_intent(setup, monkeypatch, point):
    target, control, evidence, remote = setup

    def interrupt(name, pause):
        if name == point:
            raise RuntimeError("interrupted")

    monkeypatch.setattr(executor, "checkpoint", interrupt)
    with pytest.raises(RuntimeError, match="interrupted"):
        executor.publish(target, control, evidence, initialize=True)
    with StateStore(control, evidence) as store:
        intent = store.state["tasks"]["publish"]["intent"]
        assert store.state["tasks"]["publish"]["status"] == "running"
    monkeypatch.setattr(executor, "checkpoint", lambda *args: None)
    executor.publish(target, control, evidence)
    assert (remote.pushes, remote.creates) == (1, 1)
    with StateStore(control, evidence) as store:
        assert store.state["tasks"]["publish"]["intent"] == intent
        assert store.state["rounds_used"] == 1


def test_unknown_create_failure_denies_retry(setup):
    target, control, evidence, remote = setup
    remote.fail_create = True
    with pytest.raises(RuntimeError, match="network"):
        executor.publish(target, control, evidence, initialize=True)
    with pytest.raises(ProtocolError, match="unknown create outcome"):
        executor.publish(target, control, evidence)
    assert remote.creates == 1


@pytest.mark.parametrize("change", ["duplicate", "head", "base", "closed", "fork", "draft"])
def test_remote_drift_denies_publication(setup, change):
    target, control, evidence, remote = setup
    executor.publish(target, control, evidence, initialize=True)
    if change == "duplicate":
        remote.rows *= 2
    else:
        field, value = {
            "head": ("headRefOid", B),
            "base": ("baseRefOid", A),
            "closed": ("state", "CLOSED"),
            "fork": ("headRepository", {"nameWithOwner": "x/y"}),
            "draft": ("isDraft", False),
        }[change]
        remote.rows[0][field] = value
    with pytest.raises(ProtocolError):
        executor.publish(target, control, evidence)
    assert remote.creates == 1


def test_changed_target_cannot_reuse_control(setup):
    target, control, evidence, remote = setup
    executor.publish(target, control, evidence, initialize=True)
    with pytest.raises(ProtocolError, match="target drift"):
        executor.publish(replace(target, repository="another/sandbox"), control, evidence)
    assert remote.creates == 1


@pytest.mark.parametrize(
    "repository,branch",
    [
        ("ad1896git/ResearchBase", "pipeline-test/x"),
        ("test/sandbox", "feature/x"),
        ("--bad", "pipeline-test/x"),
    ],
)
def test_config_rejects_unauthorized_targets(tmp_path, repository, branch):
    target = executor.Target(repository, "main", branch, str(tmp_path), A, B)
    config = tmp_path / "target.json"
    config.write_text(json.dumps(asdict(target)))
    with pytest.raises(ProtocolError):
        executor.Target.load(config)


def test_remote_query_failure_never_pushes_or_creates(setup, monkeypatch):
    target, control, evidence, remote = setup

    def unavailable(self):
        raise RuntimeError("remote query unavailable")

    monkeypatch.setattr(remote, "prs", unavailable)
    with pytest.raises(RuntimeError, match="query unavailable"):
        executor.publish(target, control, evidence, initialize=True)
    assert (remote.pushes, remote.creates) == (0, 0)


def test_unexpected_remote_branch_never_overwrites_or_creates(setup):
    target, control, evidence, remote = setup
    remote.branch = B
    with pytest.raises(ProtocolError, match="branch drift"):
        executor.publish(target, control, evidence, initialize=True)
    assert (remote.pushes, remote.creates) == (0, 0)


def test_missing_established_target_binding_denies_restart(setup):
    target, control, evidence, remote = setup
    executor.publish(target, control, evidence, initialize=True)
    (control / "executor-target.json").unlink()
    with pytest.raises(ProtocolError, match="missing established target"):
        executor.publish(target, control, evidence)
    assert remote.creates == 1


def test_exhausted_budget_cannot_publish(setup):
    target, control, evidence, remote = setup
    with StateStore(control, evidence, create=True) as store:
        executor.atomic_write(control / "executor-target.json", executor.encoded(asdict(target)))
        for index in range(40):
            name = f"historical-{index}"
            store.add(name)
            store.begin(name, "worker", name, A, B)
    with pytest.raises(ProtocolError, match="budget exhausted"):
        executor.publish(target, control, evidence)
    assert (remote.pushes, remote.creates) == (0, 0)


def test_library_entry_also_denies_main_repository(setup):
    target, control, evidence, remote = setup
    with pytest.raises(ProtocolError, match="main repo denied"):
        executor.publish(replace(target, repository="ad1896git/ResearchBase"), control, evidence)
    assert (remote.pushes, remote.creates) == (0, 0)
