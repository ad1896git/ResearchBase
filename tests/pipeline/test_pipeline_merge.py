"""External merge effects need frozen authorization and crash-safe host evidence."""

import hashlib
import json
from copy import deepcopy

import pytest
from scripts import pipeline_merge as merger
from scripts import pipeline_wakeup as wakeup
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    ExecutionReceipt,
    ProtocolError,
    Publication,
    StateStore,
    encoded,
)

A, B, C, D = (letter * 40 for letter in "abcd")
REPO = "ad1896git/researchbase-pipeline-sandbox"


@pytest.fixture
def case(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "proof.txt").write_text("proof")
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True, merge_approvers=frozenset({"owner"})) as s:
        s.add("publish")
        s.begin("publish", "publish", "topic", A, B)
        s.reconcile_publication("publish", Publication("topic", A, B, 1))
        for kind in ("verify", "review"):
            s.add(kind)
            intent = s.begin(kind, kind, "pr:1", A, B)
            assert intent is not None
            s.finish(
                json.dumps(
                    dict(
                        task_id=kind,
                        attempt=1,
                        result="pass",
                        commit=A,
                        evidence=[
                            dict(path="proof.txt", sha256=hashlib.sha256(b"proof").hexdigest())
                        ],
                        notes="offline acceptance fixture",
                    )
                ),
                ExecutionReceipt(kind, 1, intent["id"], A, 0, "pr:1"),
            )
        s.add("merge", needs=("publish", "verify", "review"))
        s.await_merge(
            "merge",
            Publication("topic", A, B, 1),
            after_event=5,
            checks=[dict(name=n, head=A, conclusion="success") for n in EXPECTED_CHECKS],
            proofs=("publish", "verify", "review"),
        )
    auth = tmp_path / "authorization.json"
    auth.write_bytes(
        encoded(dict(version=1, tasks=[dict(id="T01", risk="medium", authorized=True)]))
    )
    policy = dict(
        version=1,
        enabled=True,
        allow_low_risk=True,
        execution_actor="bot",
        authorization_file=str(auth),
        authorization_sha256=hashlib.sha256(auth.read_bytes()).hexdigest(),
        targets={"entry": dict(backlog_id="T01", scope_kind="implementation")},
        sandbox_rehearsal=True,
        round_budget=5,
    )
    normalized = dict(
        pr=dict(number=1, state="OPEN", isDraft=False, headRefOid=A, baseRefOid=B),
        labels={"approved-merge"},
        effective=(6, "owner"),
        cursor=6,
        checks=[dict(name=n, head=A, conclusion="success") for n in EXPECTED_CHECKS],
        outcome="pass",
    )
    remote = dict(
        number=1,
        draft=False,
        state="open",
        merged=False,
        merged_by=None,
        merge_commit_sha=None,
        changed_files=1,
        head=dict(sha=A, ref="pipeline-test/unit", repo=dict(full_name=REPO)),
        base=dict(sha=B, ref="main"),
    )
    fixture: dict = dict(
        control=control,
        evidence=evidence,
        policy=policy,
        auth=auth,
        normalized=normalized,
        remote=remote,
        puts=[],
        settings=dict(allow_squash_merge=True, delete_branch_on_merge=False),
        files=[dict(filename="change.txt", status="added")],
        base=B,
        source=A,
        protection=dict(
            required_status_checks=dict(
                strict=True, checks=[dict(context=n, app_id=15368) for n in EXPECTED_CHECKS]
            ),
            enforce_admins=dict(enabled=True),
        ),
    )

    def get(endpoint, *, pages=False):
        if endpoint == "user":
            return dict(login="bot")
        if endpoint.endswith("/pulls/1"):
            return deepcopy(remote)
        if endpoint.endswith("/pulls/1/files?per_page=100"):
            return [fixture["files"]]
        if endpoint.endswith("/git/ref/heads/main"):
            return dict(object=dict(sha=fixture["base"]))
        if endpoint.endswith("/git/ref/heads/pipeline-test/unit"):
            return dict(object=dict(sha=fixture["source"]))
        if endpoint.endswith("/git/commits/" + A):
            return dict(tree=dict(sha=C))
        if "/compare/" in endpoint:
            return dict(behind_by=0, merge_base_commit=dict(sha=B))
        if endpoint.endswith("/git/commits/" + D):
            return dict(
                tree=dict(sha=C), parents=[dict(sha=B)], message=fixture["puts"][0]["commit_title"]
            )
        if endpoint.endswith("/branches/main/protection"):
            return fixture["protection"]
        if endpoint in (f"repos/{REPO}", f"repos/{merger.MAIN}"):
            return fixture["settings"]
        pytest.fail(endpoint)

    def put(repository, number, request):
        assert number == 1 and request["sha"] == A and request["merge_method"] == "squash"
        fixture["puts"].append(request)
        remote.update(merged=True, state="closed", merged_by=dict(login="bot"), merge_commit_sha=D)
        return dict(merged=True, sha=D)

    monkeypatch.setattr(merger, "get", get)
    monkeypatch.setattr(merger, "put_merge", put)
    monkeypatch.setattr(wakeup, "observe", lambda *a: deepcopy(normalized))
    return fixture


def execute(case, **kwargs):
    with StateStore(case["control"], case["evidence"], merge_approvers=frozenset({"owner"})) as s:
        result = merger.execute_merge(
            s, "merge", REPO, policy=case["policy"], entry_id="entry", **kwargs
        )
        return result, deepcopy(s.state)


def risk(case, value):
    case["auth"].write_bytes(
        encoded(dict(version=1, tasks=[dict(id="T01", risk=value, authorized=True)]))
    )
    case["policy"]["authorization_sha256"] = hashlib.sha256(case["auth"].read_bytes()).hexdigest()


def test_authorized_squash_persists_real_effect_receipt_and_reopens(case):
    result, state = execute(case)
    assert result == "done" and state["tasks"]["merge"]["intent"]["kind"] == "merge"
    assert state["rounds_used"] == 4 and len(case["puts"]) == 1
    with StateStore(case["control"], case["evidence"]) as s:
        assert s.state["tasks"]["merge"]["status"] == "done"
    assert execute(case)[0] == "done" and len(case["puts"]) == 1
    assert not any("delete" in k for k in case["puts"][0])


@pytest.mark.parametrize("level", ["medium", "high"])
@pytest.mark.parametrize("actor", [None, "stranger"])
def test_medium_high_require_effective_owner_label(case, level, actor):
    risk(case, level)
    case["normalized"].update(
        effective=None if actor is None else (6, actor),
        labels=set() if actor is None else {"approved-merge"},
    )
    result, state = execute(case)
    assert result == "awaiting_merge" and not case["puts"]
    assert state["tasks"]["merge"]["status"] == "awaiting_merge"


def test_low_risk_requires_explicit_live_policy_but_not_label(case):
    risk(case, "low")
    case["normalized"].update(effective=None, labels=set())
    assert execute(case)[0] == "done" and len(case["puts"]) == 1


def test_low_risk_manual_policy_still_needs_owner_label(case):
    risk(case, "low")
    case["policy"]["allow_low_risk"] = False
    case["normalized"].update(effective=None, labels=set())
    assert execute(case)[0] == "awaiting_merge" and not case["puts"]


def test_merge_effect_cannot_spend_past_existing_round_budget(case):
    case["policy"]["round_budget"] = 3
    result, state = execute(case)
    assert result == "blocked" and state["rounds_used"] == 3 and not case["puts"]
    assert "budget exhausted" in state["tasks"]["merge"]["reason"]


@pytest.mark.parametrize(
    "mutation",
    [
        "disabled",
        "unknown_risk",
        "authorization_drift",
        "architecture",
        "delete_setting",
        "file_delete",
        "file_rename",
        "architecture_file",
        "base_ref_drift",
        "head_drift",
        "base_drift",
        "proof_drift",
        "foreign_actor",
    ],
)
def test_unsafe_or_unknown_inputs_block_without_put(case, mutation, monkeypatch):
    if mutation == "disabled":
        case["policy"]["enabled"] = False
    elif mutation == "unknown_risk":
        risk(case, "unknown")
    elif mutation == "authorization_drift":
        case["auth"].write_text("{}")
    elif mutation == "architecture":
        case["policy"]["targets"]["entry"]["scope_kind"] = "architecture"
    elif mutation == "delete_setting":
        case["settings"]["delete_branch_on_merge"] = True
    elif mutation == "file_delete":
        case["files"][0]["status"] = "removed"
    elif mutation == "file_rename":
        case["files"][0]["status"] = "renamed"
    elif mutation == "architecture_file":
        case["files"][0]["filename"] = "docs/architecture/change.md"
    elif mutation == "base_ref_drift":
        case["base"] = C
    elif mutation == "head_drift":
        case["normalized"]["pr"]["headRefOid"] = C
    elif mutation == "base_drift":
        case["normalized"]["pr"]["baseRefOid"] = C
    elif mutation == "proof_drift":
        (case["control"] / "results/review-1.json").write_text("{}")
    elif mutation == "foreign_actor":
        get = merger.get
        monkeypatch.setattr(
            merger, "get", lambda e, **k: dict(login="stranger") if e == "user" else get(e, **k)
        )
    if mutation == "proof_drift":
        with pytest.raises(ProtocolError):
            execute(case)
    else:
        assert execute(case)[0] == "blocked"
    assert not case["puts"]


@pytest.mark.parametrize("mutation", ["pending", "failed"])
def test_ci_not_ready_does_not_send_merge(case, mutation):
    case["normalized"]["outcome"] = mutation
    assert execute(case)[0] == "awaiting_merge" and not case["puts"]


class Crash(BaseException):
    pass


@pytest.mark.parametrize("phase", ["before-request", "after-merge"])
def test_durable_pre_post_effect_crash_recovery_at_most_once(case, monkeypatch, phase):
    def crash(name, pause):
        if name == phase:
            raise Crash()

    monkeypatch.setattr(merger, "checkpoint", crash)
    with pytest.raises(Crash):
        execute(case)
    assert len(case["puts"]) == (1 if phase == "after-merge" else 0)
    monkeypatch.setattr(merger, "checkpoint", lambda *a: None)
    assert execute(case)[0] == "done" and len(case["puts"]) == 1


def test_ambiguous_pre_http_window_blocks_and_never_retries(case, monkeypatch):
    def crash(name, pause):
        if name == "unknown-request-window":
            raise Crash()

    monkeypatch.setattr(merger, "checkpoint", crash)
    with pytest.raises(Crash):
        execute(case)
    monkeypatch.setattr(merger, "checkpoint", lambda *a: None)
    assert execute(case)[0] == "blocked" and not case["puts"]
    assert (case["control"] / "merge-operations/merge/requested.json").is_file()


def test_revoked_or_reapplied_approval_is_not_reused_on_restart(case, monkeypatch):
    def crash(name, pause):
        if name == "before-request":
            raise Crash()

    monkeypatch.setattr(merger, "checkpoint", crash)
    with pytest.raises(Crash):
        execute(case)
    monkeypatch.setattr(merger, "checkpoint", lambda *a: None)
    case["normalized"].update(effective=(7, "stranger"), cursor=7)
    assert execute(case)[0] == "awaiting_merge" and not case["puts"]
    case["normalized"].update(effective=(8, "owner"), cursor=8)
    assert execute(case)[0] == "blocked" and not case["puts"]


def test_valid_reapproval_during_final_check_blocks_before_any_put(case, monkeypatch):
    def change(name, pause):
        if name == "before-request":
            case["normalized"].update(effective=(7, "owner"), cursor=7)

    monkeypatch.setattr(merger, "checkpoint", change)
    result, state = execute(case)
    assert result == "blocked" and not case["puts"]
    assert "final approval differs" in state["tasks"]["merge"]["reason"]


@pytest.mark.parametrize("bad", ["parent", "tree", "marker", "source_branch"])
def test_unexpected_post_merge_effect_blocks_without_second_put(case, monkeypatch, bad):
    original = merger.get

    def get(endpoint, **kwargs):
        row = deepcopy(original(endpoint, **kwargs))
        if endpoint.endswith("/git/commits/" + D):
            if bad == "parent":
                row["parents"] = [dict(sha=C)]
            elif bad == "tree":
                row["tree"]["sha"] = B
            elif bad == "marker":
                row["message"] = "external operation"
        if bad == "source_branch" and endpoint.endswith("/git/ref/heads/pipeline-test/unit"):
            row["object"]["sha"] = B
        return row

    monkeypatch.setattr(merger, "get", get)
    assert execute(case)[0] == "blocked" and len(case["puts"]) == 1


def test_completed_receipt_tampering_is_rejected_on_reopen(case):
    assert execute(case)[0] == "done"
    effect = case["control"] / "merge-operations/merge/effect.json"
    value = json.loads(effect.read_text())
    value["risk"] = "low"
    effect.write_bytes(encoded(value))
    with pytest.raises(ProtocolError):
        with StateStore(case["control"], case["evidence"]):
            pass


@pytest.mark.parametrize("mode", ["v1_manual", "v2_manual", "v2_enabled"])
def test_wakeup_only_executes_after_explicit_policy_deployment(case, tmp_path, monkeypatch, mode):
    monkeypatch.setattr(wakeup, "source_guard", lambda c: None)
    jobs = tmp_path / "jobs.json"
    jobs.write_text("{}")
    queue = tmp_path / "queue.json"
    queue.write_bytes(
        encoded(
            dict(
                version=1,
                entries=[
                    dict(
                        id="entry",
                        control=str(case["control"]),
                        evidence=str(case["evidence"]),
                        checkout=str(case["evidence"]),
                        jobs=str(jobs),
                        jobs_sha256=hashlib.sha256(jobs.read_bytes()).hexdigest(),
                        repository=REPO,
                    )
                ],
            )
        )
    )
    policy = deepcopy(case["policy"])
    policy["enabled"] = mode == "v2_enabled"
    config = dict(
        root=str(tmp_path / "timer"),
        queue=str(queue),
        approvers=["owner"],
        version=1 if mode == "v1_manual" else 2,
        merge_policy=policy,
    )
    result: dict = wakeup.wake(config)
    assert result["entries"]["entry"] == ("done" if mode == "v2_enabled" else "awaiting_merge")
    assert len(case["puts"]) == (1 if mode == "v2_enabled" else 0)


def test_production_missing_strict_protection_cannot_send_put(case):
    case["protection"]["required_status_checks"]["strict"] = False
    case["policy"]["sandbox_rehearsal"] = False
    case["remote"]["head"]["repo"]["full_name"] = merger.MAIN
    with StateStore(case["control"], case["evidence"], merge_approvers=frozenset({"owner"})) as s:
        assert (
            merger.execute_merge(s, "merge", merger.MAIN, policy=case["policy"], entry_id="entry")
            == "blocked"
        )
    assert not case["puts"]


@pytest.mark.parametrize("released", [True, False])
def test_production_requires_executor_commit_already_on_main(monkeypatch, released):
    monkeypatch.setattr(merger, "run", lambda *a, **k: "" if "status" in a else A)
    monkeypatch.setattr(
        merger,
        "get",
        lambda e: dict(
            ahead_by=0 if released else 1,
            merge_base_commit=dict(sha=A if released else B),
        ),
    )
    if released:
        merger.released_source_guard()
    else:
        with pytest.raises(ProtocolError, match="already released"):
            merger.released_source_guard()
