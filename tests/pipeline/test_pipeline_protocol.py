"""Executable offline acceptance cases for protocol v1; no live pipeline effects."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    ExecutionReceipt,
    ProtocolError,
    Publication,
    StateStore,
    report,
)
from scripts.pipeline_safety import SafetyError

ROOT = Path(__file__).resolve().parents[2]
A, B, C = "a" * 40, "b" * 40, "c" * 40
ENV = dict(os.environ, PYTHONPATH=str(ROOT))


def checks(head=A):
    return [dict(name=n, head=head, conclusion="success") for n in EXPECTED_CHECKS]


def output(evidence, *, result="pass", attempt=1, task_id="work", commit=A):
    data = (evidence / "test.log").read_bytes()
    return json.dumps(
        dict(
            task_id=task_id,
            attempt=attempt,
            result=result,
            commit=commit,
            evidence=[dict(path="test.log", sha256=hashlib.sha256(data).hexdigest())],
            notes="literal report, not authority",
        )
    )


@pytest.fixture
def paths(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    executed = subprocess.run(
        [sys.executable, "-c", "print('actual host test execution')"],
        capture_output=True,
        check=True,
    )
    (evidence / "test.log").write_bytes(executed.stdout)
    return tmp_path / "control", evidence


def test_crash_after_durable_result_recovers_without_rerunning(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
    program = """import os,sys,json
from pathlib import Path
from scripts.pipeline_protocol import StateStore, ExecutionReceipt
with StateStore(Path(sys.argv[1]),Path(sys.argv[2])) as store:
    intent=store.begin('work','worker','job-1',sys.argv[4],sys.argv[5])
    store._save=lambda value: os._exit(71)
    store.finish(sys.argv[3],ExecutionReceipt('work',1,intent['id'],sys.argv[4],0))
"""
    crashed = subprocess.run(
        [sys.executable, "-c", program, str(control), str(evidence), output(evidence), A, B],
        env=ENV,
    )
    assert crashed.returncode == 71
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        assert store.state["tasks"]["work"]["status"] == "running"
        store.recover_result("work")
        assert store.state["tasks"]["work"]["status"] == "done"
        assert store.state["rounds_used"] == 1
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as restored:
        assert restored.state["tasks"]["work"]["status"] == "done"


def test_push_and_pr_created_before_crash_are_reconciled_not_recreated(paths, tmp_path):
    control, evidence = paths
    remote, source = tmp_path / "remote.git", tmp_path / "source"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "base",
        ],
        check=True,
    )
    head = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("publish")
    # Real Git push plus a durable PR service test double; not live GitHub evidence.
    program = """import os,sys,json,subprocess
from pathlib import Path
from scripts.pipeline_protocol import StateStore
control,evidence,source,remote,head=sys.argv[1:]
with StateStore(Path(control),Path(evidence)) as store:
    store.begin('publish','publish','refs/heads/topic',head,head)
    subprocess.run(['git','-C',source,'push',remote,'HEAD:refs/heads/topic'],check=True)
    Path(remote,'pr.json').write_text(json.dumps(dict(pr=17,creates=1,head=head,base=head)))
    os._exit(73)
"""
    crashed = subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            str(control),
            str(evidence),
            str(source),
            str(remote),
            head,
        ],
        env=ENV,
    )
    assert crashed.returncode == 73
    assert (
        subprocess.check_output(
            ["git", "--git-dir", str(remote), "rev-parse", "topic"], text=True
        ).strip()
        == head
    )
    observed = json.loads((remote / "pr.json").read_text())
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.reconcile_publication(
            "publish", Publication("refs/heads/topic", head, head, observed["pr"])
        )
        assert store.state["tasks"]["publish"]["status"] == "done"
        with pytest.raises(ProtocolError, match="not eligible"):
            store.begin("publish", "publish", "refs/heads/topic", head, head)
    assert json.loads((remote / "pr.json").read_text())["creates"] == 1


@pytest.mark.parametrize("bad", ["", "{", "null", "{}", '{"task_id":"x","task_id":"x"}', "NaN"])
def test_missing_or_malformed_output_never_becomes_pass(paths, bad):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
        intent = store.begin("work", "worker", "job", A, B)
        assert intent is not None
        with pytest.raises(ProtocolError):
            store.finish(bad, ExecutionReceipt("work", 1, intent["id"], A, 0))
        assert store.state["tasks"]["work"]["status"] == "running"
        assert store.state["tasks"]["work"]["result"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("attempt", True),
        ("result", "PASS"),
        ("commit", B.upper()),
        ("evidence", []),
        ("extra", "unknown"),
    ],
)
def test_wrong_structured_fields_rejected(paths, field, value):
    _, evidence = paths
    parsed = json.loads(output(evidence))
    parsed[field] = value
    with pytest.raises(ProtocolError):
        report(json.dumps(parsed), evidence)


def test_claimed_pass_does_not_override_host_failure_or_lose_history(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
        intent = store.begin("work", "worker", "job", A, B)
        assert intent is not None
        store.finish(output(evidence), ExecutionReceipt("work", 1, intent["id"], A, 9))
        assert store.state["tasks"]["work"]["status"] == "failed"
        receipt = control / "results/work-1.json"
        original = receipt.read_bytes()
        with pytest.raises(ProtocolError, match="not eligible"):
            store.begin("work", "worker", "job", A, B)
        assert receipt.read_bytes() == original


def test_awaiting_merge_does_not_block_independent_tasks(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("merge")
        store.add("dependent", needs=("merge",))
        store.add("independent")
        store.await_merge("merge", Publication("topic", A, B, 38), after_event=10, checks=checks())
        assert store.eligible(0) == ["independent"]
        assert not store.merge_allowed("merge", head=A, base=B, checks=checks(), labels=[])
        store.approve_label(
            "merge", event_id=11, label="approved-merge", pr=38, head=A, base=B, actor="owner"
        )
        assert store.merge_allowed(
            "merge", head=A, base=B, checks=checks(), labels=["approved-merge"]
        )


@pytest.mark.parametrize("head,base", [(C, B), (A, C)])
def test_head_or_base_drift_invalidates_approval_permanently(paths, head, base):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("merge")
        store.await_merge("merge", Publication("topic", A, B, 38), after_event=10, checks=checks())
        store.approve_label(
            "merge", event_id=11, label="approved-merge", pr=38, head=A, base=B, actor="owner"
        )
        assert not store.merge_allowed(
            "merge", head=head, base=base, checks=checks(head), labels=["approved-merge"]
        )
        assert not store.merge_allowed(
            "merge", head=A, base=B, checks=checks(), labels=["approved-merge"]
        )


def test_stale_label_removal_and_reapplication(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("merge")
        store.await_merge("merge", Publication("topic", A, B, 38), after_event=10, checks=checks())
        with pytest.raises(ProtocolError):
            store.approve_label(
                "merge", event_id=10, label="approved-merge", pr=38, head=A, base=B, actor="owner"
            )
        store.approve_label(
            "merge", event_id=11, label="approved-merge", pr=38, head=A, base=B, actor="owner"
        )
        assert not store.merge_allowed("merge", head=A, base=B, checks=checks(), labels=[])
        with pytest.raises(ProtocolError):
            store.approve_label(
                "merge", event_id=11, label="approved-merge", pr=38, head=A, base=B, actor="owner"
            )
        store.approve_label(
            "merge", event_id=12, label="approved-merge", pr=38, head=A, base=B, actor="owner"
        )
        assert store.merge_allowed(
            "merge", head=A, base=B, checks=checks(), labels=["approved-merge"]
        )


@pytest.mark.parametrize("change", ["missing", "failed", "wrong_head", "duplicate"])
def test_no_merge_for_incomplete_wrong_or_failed_ci(paths, change):
    control, evidence = paths
    bad = checks()
    if change == "missing":
        bad.pop()
    if change == "failed":
        bad[0]["conclusion"] = "failure"
    if change == "wrong_head":
        bad[0]["head"] = C
    if change == "duplicate":
        bad.append(dict(bad[0]))
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("merge")
        with pytest.raises(ProtocolError, match="CI not ready"):
            store.await_merge("merge", Publication("topic", A, B, 38), after_event=0, checks=bad)


def test_quota_wait_does_not_consume_rounds_and_budget_exhaustion_is_distinct(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
        store.begin("work", "worker", "job", A, B, max_rounds=1)
        store.quota("work", 100)
        for now in range(100):
            assert store.eligible(now) == []
        assert store.state["rounds_used"] == 1
        assert store.begin("work", "worker", "job", A, B, now=100, max_rounds=1) is None
        assert store.state["tasks"]["work"]["status"] == "budget_exhausted"


@pytest.mark.parametrize("kind", ["delete", "architecture"])
def test_deletion_and_architecture_always_require_human_decision(paths, kind):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("dangerous")
        store.add("independent")
        assert store.begin("dangerous", kind, "target", A, B) is None
        assert store.state["tasks"]["dangerous"]["status"] == "blocked"
        assert store.eligible(0) == ["independent"]


def test_unknown_publication_is_not_blindly_retried(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("publish")
        store.begin("publish", "publish", "topic", A, B)
        store.reconcile_publication("publish", None)
        assert store.state["tasks"]["publish"]["status"] == "blocked"
        assert store.eligible(0) == []


def test_existing_state_with_missing_receipt_is_rejected(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
        intent = store.begin("work", "worker", "job", A, B)
        assert intent is not None
        store.finish(output(evidence), ExecutionReceipt("work", 1, intent["id"], A, 0))
    (control / "results/work-1.json").unlink()
    with pytest.raises(ProtocolError, match="missing completion"):
        with StateStore(control, evidence, merge_approvers=frozenset({"owner"})):
            pass


def test_modified_evidence_is_rejected_on_recovery(paths):
    control, evidence = paths
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        store.add("work")
        intent = store.begin("work", "worker", "job", A, B)
        assert intent is not None
        store.finish(output(evidence), ExecutionReceipt("work", 1, intent["id"], A, 0))
    (evidence / "test.log").write_text("tampered")
    with pytest.raises(ProtocolError, match="hash mismatch"):
        with StateStore(control, evidence, merge_approvers=frozenset({"owner"})):
            pass


def test_two_protocol_writers_cannot_enter_the_same_store(paths):
    control, evidence = paths
    program = """import sys
from pathlib import Path
from scripts.pipeline_protocol import StateStore
with StateStore(Path(sys.argv[1]),Path(sys.argv[2])):
    print('locked',flush=True)
    sys.stdin.readline()
"""
    owner = subprocess.Popen(
        [sys.executable, "-u", "-c", program, str(control), str(evidence)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=ENV,
    )
    try:
        assert owner.stdout is not None
        assert owner.stdout.readline().strip() == "locked"
        with pytest.raises(SafetyError, match="lock already held"):
            with StateStore(control, evidence):
                pass
    finally:
        owner.communicate("\n", timeout=10)


def test_existing_running_resource_is_not_reassigned_after_restart(paths):
    control, evidence = paths
    with StateStore(control, evidence) as store:
        store.add("first")
        store.add("second")
        store.begin("first", "worker", "lane-1", A, B)
    with StateStore(control, evidence) as resumed:
        with pytest.raises(ProtocolError, match="unreconciled execution"):
            resumed.begin("second", "worker", "lane-1", A, B)
        assert resumed.state["tasks"]["first"]["status"] == "running"


def test_default_policy_and_unauthorized_actor_cannot_approve_merge(paths):
    control, evidence = paths
    with StateStore(control, evidence) as store:
        store.add("merge")
        store.await_merge("merge", Publication("topic", A, B, 38), after_event=10, checks=checks())
        with pytest.raises(ProtocolError, match="not authorized"):
            store.approve_label(
                "merge", event_id=11, label="approved-merge", pr=38, head=A, base=B, actor="owner"
            )
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        with pytest.raises(ProtocolError, match="not authorized"):
            store.approve_label(
                "merge", event_id=12, label="approved-merge", pr=38, head=A, base=B, actor="worker"
            )


def test_state_revision_conflict_does_not_overwrite_external_change(paths):
    control, evidence = paths
    with StateStore(control, evidence) as store:
        store.add("work")
        other = json.loads((control / "state.json").read_text())
        other["revision"] += 1
        (control / "state.json").write_text(json.dumps(other))
        before = (control / "state.json").read_bytes()
        with pytest.raises(ProtocolError, match="revision conflict"):
            store.begin("work", "worker", "job", A, B)
        assert (control / "state.json").read_bytes() == before


def test_duplicate_and_unknown_state_fields_fail_closed(paths):
    control, evidence = paths
    with StateStore(control, evidence):
        pass
    good = (control / "state.json").read_text()
    for bad in (
        good.replace('"version": 1', '"version": 1, "version": 1'),
        good[:-2] + ',"unknown":0}',
    ):
        (control / "state.json").write_text(bad)
        with pytest.raises(ProtocolError):
            with StateStore(control, evidence):
                pass


def test_result_schema_and_runtime_closed_fields_agree():
    schema = json.loads((ROOT / "scripts/pipeline_result.schema.json").read_text())
    assert set(schema["required"]) == {
        "task_id",
        "attempt",
        "result",
        "commit",
        "evidence",
        "notes",
    }
    assert schema["additionalProperties"] is False


def test_receipt_for_another_commit_cannot_make_report_pass(paths):
    control, evidence = paths
    with StateStore(control, evidence) as store:
        store.add("work")
        intent = store.begin("work", "verify", "job", A, B)
        assert intent is not None
        with pytest.raises(ProtocolError, match="execution binding mismatch"):
            store.finish(output(evidence), ExecutionReceipt("work", 1, intent["id"], C, 0))
        assert store.state["tasks"]["work"]["status"] == "running"
