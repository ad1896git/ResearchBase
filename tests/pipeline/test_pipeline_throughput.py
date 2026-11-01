"""Admission authority, finite CI ticks and actual kernel resource ownership."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import pipeline_admission as admission
from scripts import pipeline_capability as capability
from scripts import pipeline_ci as ci
from scripts import pipeline_throughput as scheduler
from scripts import pipeline_worker as worker
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    ExecutionReceipt,
    ProtocolError,
    StateStore,
    encoded,
)
from scripts.pipeline_safety import ProcessLock


def frozen(path, value):
    path.write_bytes(encoded(value))
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def git(source, *args):
    return subprocess.check_output(["git", *args], cwd=source, text=True).strip()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-q")
    git(source, "config", "user.name", "test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "code.py").write_text("value = 1\n")
    (source / "other.py").write_text("unchanged = True\n")
    git(source, "add", "code.py", "other.py")
    git(source, "commit", "-qm", "frozen source")
    git(source, "remote", "add", "origin", "https://github.com/ad1896git/ResearchBase.git")
    head = git(source, "rev-parse", "HEAD")
    auth = frozen(
        tmp_path / "auth.json",
        dict(
            version=1,
            tasks=[
                dict(
                    id="T01",
                    authorized=True,
                    risk="medium",
                    depends_on=[],
                    goal="bounded change",
                    acceptance="independent evidence",
                )
            ],
        ),
    )
    spec = tmp_path / "execution.md"
    spec.write_text("Frozen scope: code.py only, no governing changes.")
    contract = frozen(
        tmp_path / "contract.json",
        dict(
            version=1,
            backlog_id="T01",
            scope_kind="implementation",
            frozen=True,
            allowed_paths=["code.py"],
            specification=dict(
                path=str(spec), sha256=hashlib.sha256(spec.read_bytes()).hexdigest()
            ),
        ),
    )
    gate = frozen(
        tmp_path / "gate.json",
        dict(version=1, backlog_id="T01", contract_sha256=contract["sha256"], decision="PASS"),
    )
    template = frozen(
        tmp_path / "template.json",
        dict(
            version=1,
            implementation_prompt="Change the scoped file, commit and report actual evidence.",
            review_prompt="Read only and report source hashes and findings.",
            pg_argv=[],
        ),
    )
    index = frozen(
        tmp_path / "index.json",
        dict(
            version=1,
            contracts={"T01": dict(contract=contract, template="code", gates=[gate])},
            completed={},
            templates={"code": template},
            publications={},
        ),
    )
    policy = dict(
        version=1,
        root=str(tmp_path / "scheduler"),
        worktrees=str(tmp_path / "worktrees"),
        source_checkout=str(source),
        repository="ad1896git/ResearchBase",
        base_ref="main",
        authorization=auth,
        index=index,
        implementation_slots=2,
        review_slots=1,
        pg_slots=1,
        pg_environment={},
    )
    monkeypatch.setattr(admission, "base_head", lambda p: head)
    return dict(root=tmp_path, source=source, head=head, policy=policy, auth=auth, index=index)


def change(case, key, mutate):
    spec = case[key]
    value = json.loads(Path(spec["path"]).read_text())
    mutate(value)
    spec.update(frozen(Path(spec["path"]), value))


def test_auto_admission_uses_backlog_not_handwritten_job_packs(setup):
    result = admission.admit(setup["policy"])
    assert result == {"T01": "admitted"}
    folder = Path(setup["policy"]["root"]) / "generations/T01"
    packet = json.loads((folder / "packet.json").read_text())
    assert packet["risk"] == "medium" and packet["stages"] == ["implementation", "review"]
    before = (folder / "packet.json").read_bytes()
    assert admission.admit(setup["policy"])["T01"] == "admitted"
    assert (folder / "packet.json").read_bytes() == before


@pytest.mark.parametrize(
    "damage", ["risk", "authorization", "dependency", "contract", "gate", "scope"]
)
def test_unapproved_unknown_or_unfrozen_backlog_never_gets_a_job(setup, damage):
    if damage == "risk":
        change(setup, "auth", lambda a: a["tasks"][0].update(risk="unknown"))
    elif damage == "authorization":
        change(setup, "auth", lambda a: a["tasks"][0].update(authorized=False))
    elif damage == "dependency":
        change(setup, "auth", lambda a: a["tasks"][0].update(depends_on=["D01"]))
    else:
        index = json.loads(Path(setup["index"]["path"]).read_text())
        item = index["contracts"]["T01"]
        if damage == "contract":
            index["contracts"] = {}
        elif damage == "gate":
            item["gates"] = []
        else:
            path = Path(item["contract"]["path"])
            value = json.loads(path.read_text())
            value["scope_kind"] = "architecture"
            item["contract"] = frozen(path, value)
        setup["policy"]["index"] = frozen(Path(setup["index"]["path"]), index)
    result = admission.admit(setup["policy"])
    assert result["T01"].startswith("held:")
    assert not (Path(setup["policy"]["root"]) / "generations/T01/packet.json").exists()


def stage(case, name="implementation"):
    admission.admit(case["policy"])
    folder = Path(case["policy"]["root"]) / "generations/T01"
    packet = json.loads((folder / "packet.json").read_text())
    row, checkout, template = admission.prepare_stage(case["policy"], folder, packet, name)
    return folder, row, checkout, worker.WorkerJob(**json.loads((row / "job.json").read_text()))


def test_main_worker_requires_host_capability_and_frozen_inputs(setup):
    _, row, checkout, job = stage(setup)
    job.validate(row / "ledger", checkout)
    from dataclasses import replace

    with pytest.raises(ProtocolError, match="denied"):
        replace(job, capability_file="", capability_sha256="").validate(row / "ledger", checkout)
    Path(setup["auth"]["path"]).write_text("{}")
    with pytest.raises(ProtocolError, match="drift"):
        job.validate(row / "ledger", checkout)


@pytest.mark.parametrize(
    "name", ["AGENTS.md", "docs/architecture/new.md", ".github/workflows/x.yml"]
)
def test_governing_and_architecture_paths_never_granted_by_broad_patterns(name):
    assert not capability.allowed(name, ["**"])


def test_main_output_outside_frozen_scope_is_not_done(setup):
    _, row, checkout, job = stage(setup)
    (checkout / "unapproved.txt").write_text("outside frozen scope")
    with pytest.raises(ProtocolError, match="outside"):
        capability.validate_capability(job, row / "ledger", completed=True)


def test_incomplete_launch_blocks_and_quarantines_not_relaunches(setup, monkeypatch):
    folder, row, checkout, _ = stage(setup)
    (row / "ledger/throughput-launch-work.json").write_text("{}")
    monkeypatch.setattr(scheduler, "prepare_stage", lambda *args: (row, checkout, {}))
    monkeypatch.setattr(
        scheduler.subprocess, "Popen", lambda *a, **k: pytest.fail("duplicate launch")
    )
    packet = json.loads((folder / "packet.json").read_text())
    assert scheduler.launch(setup["policy"], folder, packet, "implementation") == "blocked"
    assert (Path(setup["policy"]["root"]) / "quarantine.json").is_file()
    with StateStore(row / "ledger", checkout) as store:
        assert store.state["tasks"]["work"]["attempt"] == 0
        assert store.state["tasks"]["work"]["status"] == "blocked"


def test_missing_pg_profile_is_held_without_starting_any_process(setup):
    assert scheduler.launch(setup["policy"], Path("unused"), {}, "pg").startswith("held:")


def test_two_implementation_one_review_one_pg_are_real_separate_locks(tmp_path):
    leases = []
    try:
        for stage_name, count in (("implementation", 2), ("review", 1), ("pg", 1)):
            paths = scheduler.slot_paths(tmp_path, stage_name)
            assert len(paths) == count
            for path in paths:
                lock = ProcessLock(path)
                assert lock.acquire()
                leases.append(lock)
                contender = ProcessLock(path)
                assert not contender.acquire()
                contender.close()
    finally:
        for lease in leases:
            lease.close()


def test_inherited_kernel_lock_survives_parent_descriptor_close(tmp_path):
    lease = ProcessLock(tmp_path / "resource.lock")
    assert lease.acquire()
    assert lease.fd is not None
    child = subprocess.Popen(
        [sys.executable, "-c", "import sys;print('owned',flush=True);sys.stdin.read()"],
        pass_fds=(lease.fd,),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None and child.stdout.readline().strip() == "owned"
        lease.close()
        contender = ProcessLock(lease.path)
        assert not contender.acquire()
        child.communicate("done", timeout=10)
        assert contender.acquire()
        contender.close()
    finally:
        lease.close()
        if child.poll() is None:
            child.kill()
            child.wait()


def test_pending_tick_releases_global_lease_and_other_work_advances(setup, monkeypatch):
    policy = setup["policy"]
    change(setup, "auth", lambda a: a.update(tasks=[]))
    evidence = setup["root"] / "evidence"
    evidence.mkdir()
    (evidence / "proof.txt").write_text("proof")
    control = setup["root"] / "ci"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
        store.add("next", needs=("ci",))
    other = setup["root"] / "other"
    with StateStore(other, evidence, create=True) as store:
        store.add("other")
    target = dict(
        repository="ad1896git/researchbase-pipeline-sandbox",
        pr=1,
        branch="pipeline-test/test",
        head="a" * 40,
        base="main",
        base_commit="b" * 40,
    )
    jobs = {
        "ci": dict(kind="ci", config=target),
        "next": dict(kind="worker", config=dict(task_id="next")),
    }
    entries = []
    for name, c, j in (
        ("ci", control, jobs),
        ("other", other, {"other": dict(kind="worker", config=dict(task_id="other"))}),
    ):
        path = setup["root"] / (name + "-jobs.json")
        path.write_bytes(encoded(j))
        entries.append(
            dict(
                id=name,
                control=str(c),
                evidence=str(evidence),
                checkout=str(evidence),
                jobs=str(path),
                jobs_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                repository=target["repository"],
            )
        )
    queue = setup["root"] / "queue.json"
    queue.write_bytes(encoded(dict(version=1, entries=entries)))
    config: dict = dict(
        root=str(setup["root"] / "timer"),
        queue=str(queue),
        throughput=policy,
        merge_policy=dict(enabled=False),
        approvers=[],
    )
    monkeypatch.setattr(ci.PublishedCITarget, "validate", lambda *a, **k: None)
    pending = [True]
    observations = []

    def observe(self, **kwargs):
        probe = ProcessLock(Path(config["root"]) / "wakeup.lock")
        assert probe.acquire()
        probe.close()
        observations.append(1)
        checks = (
            []
            if pending[0]
            else [
                dict(
                    name=n,
                    head_sha="a" * 40,
                    status="completed",
                    conclusion="success",
                    app=dict(slug="github-actions"),
                )
                for n in EXPECTED_CHECKS
            ]
        )
        return dict(pr={}, check_runs=checks)

    monkeypatch.setattr(ci.CIObserver, "observe", observe)

    def finish(*args, legacy, **kwargs):
        c, e, job, name = legacy
        with StateStore(c, e) as store:
            intent = store.begin(name, "worker", name, "a" * 40, "b" * 40)
            if intent is None:
                return "blocked"
            report = dict(
                task_id=name,
                attempt=1,
                result="pass",
                commit="a" * 40,
                evidence=[dict(path="proof.txt", sha256=hashlib.sha256(b"proof").hexdigest())],
                notes="offline host fixture",
            )
            store.finish(
                json.dumps(report), ExecutionReceipt(name, 1, intent["id"], "a" * 40, 0, name)
            )
        return "done"

    monkeypatch.setattr(scheduler, "launch", finish)
    first = scheduler.tick(config)
    assert first["entries"] == dict(ci="pending", other="done") and len(observations) == 1
    with StateStore(control, evidence) as store:
        before = store.state["tasks"]["ci"]["intent"]
        assert store.state["rounds_used"] == 1
    pending[0] = False
    second = scheduler.tick(config)
    assert second["entries"]["ci"] == "done"
    with StateStore(control, evidence) as store:
        assert store.state["tasks"]["ci"]["intent"] == before
        assert store.state["tasks"]["ci"]["attempt"] == 1 and store.state["rounds_used"] == 2
        assert store.state["tasks"]["next"]["status"] == "done"


def test_index_revision_chain_keeps_active_packet_and_old_proofs(setup):
    root = Path(setup["policy"]["root"])
    admission.admit(setup["policy"])
    scheduler.policy_revision(root, setup["policy"])
    before = (root / "generations/T01/packet.json").read_bytes()
    first = json.loads((root / "policy-revision.json").read_text())["sha256"]
    next_index = setup["root"] / "index-v2.json"
    next_index.write_bytes(Path(setup["index"]["path"]).read_bytes())
    newer = dict(
        setup["policy"],
        index=dict(
            path=str(next_index), sha256=hashlib.sha256(next_index.read_bytes()).hexdigest()
        ),
    )
    scheduler.validate_policy(newer)
    scheduler.policy_revision(root, newer)
    second = json.loads((root / "policy-revision.json").read_text())["sha256"]
    assert first != second
    assert (
        json.loads((root / "policy-revisions" / (second + ".json")).read_text())["parent"] == first
    )
    admission.admit(newer)
    assert (root / "generations/T01/packet.json").read_bytes() == before
    with pytest.raises(ProtocolError, match="drift"):
        scheduler.policy_revision(root, setup["policy"])


def test_lost_admitted_packet_is_not_silently_recreated(setup):
    admission.admit(setup["policy"])
    path = Path(setup["policy"]["root"]) / "generations/T01/packet.json"
    path.unlink()
    with pytest.raises(ProtocolError, match="lost"):
        admission.admit(setup["policy"])
    assert not path.exists()


def test_one_substep_completion_never_closes_a_whole_backlog_parent(setup):
    change(setup, "auth", lambda a: a["tasks"][0].update(depends_on=["E04"]))
    evidence = setup["root"] / "actual.json"
    evidence.write_text("actual substep")
    receipt = dict(
        version=1,
        backlog_id="E04",
        status="done",
        coverage="one_substep",
        evidence=[
            dict(path=str(evidence), sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())
        ],
    )
    spec = frozen(setup["root"] / "completed.json", receipt)
    change(setup, "index", lambda i: i["completed"].update(E04=spec))
    assert admission.admit(setup["policy"])["T01"].startswith("held:")


def test_unknown_pg_command_and_incomplete_pins_are_denied(setup):
    from scripts.pipeline_pg import validate_environment

    with pytest.raises(ProtocolError, match="four"):
        validate_environment(dict(RB_TEST_ADMIN_URL="postgresql+psycopg://x@localhost/postgres"))
    index = json.loads(Path(setup["index"]["path"]).read_text())
    template = Path(index["templates"]["code"]["path"])
    data = json.loads(template.read_text())
    data["pg_argv"] = ["sh", "-c", "anything"]
    index["templates"]["code"] = frozen(template, data)
    setup["policy"]["index"] = frozen(Path(setup["index"]["path"]), index)
    assert admission.admit(setup["policy"])["T01"].startswith("held:")


def test_reviewer_cannot_commit_even_an_allowed_author_file(setup):
    folder, row, checkout, job = stage(setup)
    (checkout / "code.py").write_text("value = 2\n")
    with StateStore(row / "ledger", checkout) as store:
        intent = store.begin("work", "worker", job.key, job.head, job.base)
        assert intent is not None
        output = row / "ledger/executions/work-1"
        output.mkdir(parents=True, exist_ok=True)
        worker.snapshot_artifacts(checkout, output)
        store.finish(
            json.dumps(
                dict(
                    task_id="work",
                    attempt=1,
                    result="pass",
                    commit=job.head,
                    evidence=[
                        dict(
                            path="code.py",
                            sha256=hashlib.sha256((checkout / "code.py").read_bytes()).hexdigest(),
                        )
                    ],
                    notes="author fixture",
                )
            ),
            ExecutionReceipt("work", 1, intent["id"], job.head, 0, job.key),
        )
    packet = json.loads((folder / "packet.json").read_text())
    review, copy, _ = admission.prepare_stage(setup["policy"], folder, packet, "review")
    assert copy != checkout and copy.resolve() != checkout.resolve()
    review_job = worker.WorkerJob(**json.loads((review / "job.json").read_text()))
    (copy / "code.py").write_text("value=9\n")
    git(copy, "add", "code.py")
    git(copy, "commit", "-qm", "review may not author")
    with pytest.raises(ProtocolError, match="model changed HEAD"):
        capability.validate_capability(review_job, review / "ledger", completed=True)


def author_output(case):
    folder, row, checkout, job = stage(case)
    (checkout / "code.py").write_text("value = 2\n")
    with StateStore(row / "ledger", checkout) as store:
        intent = store.begin("work", "worker", job.key, job.head, job.base)
        assert intent is not None
        report = dict(
            task_id="work",
            attempt=1,
            result="pass",
            commit=job.head,
            evidence=[
                dict(
                    path="code.py",
                    sha256=hashlib.sha256((checkout / "code.py").read_bytes()).hexdigest(),
                )
            ],
            notes="Original model receipt, not a host candidate commit",
        )
        output = row / "ledger/executions/work-1"
        output.mkdir(parents=True, exist_ok=True)
        worker.snapshot_artifacts(checkout, output)
        output = row / "ledger/executions/work-1"
        output.mkdir(parents=True, exist_ok=True)
        worker.snapshot_artifacts(checkout, output)
        store.finish(
            json.dumps(report), ExecutionReceipt("work", 1, intent["id"], job.head, 0, job.key)
        )
    return folder, row, checkout, job


def test_host_candidate_preserves_model_receipt_and_replays_commit_once(setup):
    from scripts.pipeline_candidate import derive_candidate

    _, row, checkout, job = author_output(setup)
    receipt = (row / "ledger/results/work-1.json").read_bytes()
    effect = derive_candidate(job, row / "ledger")
    assert effect["head"] != job.head and effect["parent"] == job.head
    assert derive_candidate(job, row / "ledger") == effect
    assert (row / "ledger/results/work-1.json").read_bytes() == receipt
    assert json.loads(receipt)["report"]["commit"] == job.head
    assert git(checkout, "rev-list", "--count", f"{job.head}..HEAD") == "1"


def test_host_candidate_post_commit_crash_recovers_without_second_commit(setup, monkeypatch):
    from scripts import pipeline_candidate as candidate

    _, row, checkout, job = author_output(setup)
    original = candidate.immutable

    def interrupted(path, value):
        if path.name == "effect.json":
            raise SystemExit("local commit already happened")
        return original(path, value)

    monkeypatch.setattr(candidate, "immutable", interrupted)
    with pytest.raises(SystemExit):
        candidate.derive_candidate(job, row / "ledger")
    head = git(checkout, "rev-parse", "HEAD")
    monkeypatch.setattr(candidate, "immutable", original)
    assert candidate.derive_candidate(job, row / "ledger")["head"] == head
    assert git(checkout, "rev-list", "--count", f"{job.head}..HEAD") == "1"


def test_head_unchanged_does_not_hide_uncommitted_out_of_scope_edit(setup):
    _, row, checkout, job = stage(setup)
    (checkout / "other.py").write_text("unauthorized=True\n")
    assert git(checkout, "diff", f"{job.head}..HEAD") == ""
    with pytest.raises(ProtocolError, match="exceeds"):
        capability.validate_capability(job, row / "ledger", completed=True)


@pytest.mark.parametrize(
    "status", ["running", "capacity_wait", "retry_wait", "held: PostgreSQL profile missing"]
)
def test_generated_status_reports_actual_dispatch_result(setup, monkeypatch, status):
    admission.admit(setup["policy"])
    monkeypatch.setattr(scheduler, "launch", lambda *a, **k: status)
    assert scheduler.generated_tick(setup["policy"])["T01"] == status
    path = Path(setup["policy"]["root"]) / "generations/T01/progress.json"
    assert json.loads(path.read_text())["status"] == status


def test_unknown_executor_status_persistently_blocks(setup, monkeypatch):
    admission.admit(setup["policy"])
    monkeypatch.setattr(scheduler, "launch", lambda *a, **k: "mystery")
    assert scheduler.generated_tick(setup["policy"])["T01"].startswith("blocked:")
    assert (
        json.loads((Path(setup["policy"]["root"]) / "generations/T01/progress.json").read_text())[
            "status"
        ]
        == "blocked"
    )


def test_already_blocked_unjoined_child_still_quarantines_all_new_dispatch(setup):
    folder, row, checkout, job = stage(setup)
    with StateStore(row / "ledger", checkout) as store:
        store.begin("work", "worker", job.key, job.head, job.base)
        store.block("work", "unknown child")
    scheduler.audit_unjoined(setup["policy"], [])
    assert (Path(setup["policy"]["root"]) / "quarantine.json").is_file()
    assert scheduler.launch(setup["policy"], folder, {}, "implementation").startswith("held:")


@pytest.mark.parametrize("kind", ["implementation", "pg"])
def test_unjoined_failure_quarantines_before_resource_fd_is_closed(setup, monkeypatch, kind):
    from contextlib import nullcontext

    _, row, checkout, job = stage(setup)
    root = Path(setup["policy"]["root"])
    control = row / "ledger"
    driver = ProcessLock(control / "driver.lock")
    resource = ProcessLock(scheduler.slot_paths(root, kind)[0])
    assert driver.acquire() and resource.acquire()
    assert driver.fd is not None and resource.fd is not None
    descriptors = [driver.fd, resource.fd]
    leases = [f"{driver.fd}:{driver.path}", f"{resource.fd}:{resource.path}"]
    driver.fd = resource.fd = None  # Ownership transferred, exactly as in the child process.
    command = control / "command.json"
    (checkout / "tests").mkdir()
    (checkout / "tests/selected.py").write_text("pass\n")
    command.write_bytes(
        encoded(
            dict(
                kind=kind,
                control=str(control),
                evidence=str(checkout),
                job=json.loads((row / "job.json").read_text()),
                pg_argv=[sys.executable, "-m", "pytest", "tests/selected.py"],
                pg_environment=dict(test="offline"),
                resource_root=str(root),
            )
        )
    )

    def unjoined_worker(*args, **kwargs):
        with StateStore(control, checkout) as store:
            store.begin("work", "worker", job.key, job.head, job.base)
            store.block("work", "already blocked but descendants not stopped")
        raise RuntimeError("unjoined descendants")

    def unjoined_pg(*args):
        (control / "pg-terminal.json").write_bytes(encoded(dict(descendants_stopped=False)))
        raise RuntimeError("unjoined descendants")

    monkeypatch.setattr(scheduler, "worker_once", unjoined_worker)
    monkeypatch.setattr(scheduler, "isolated_environment", lambda env: nullcontext({}))
    monkeypatch.setattr(scheduler, "execute_pg", unjoined_pg)
    if kind == "pg":
        template = frozen(
            setup["root"] / "unjoined-template.json",
            dict(pg_argv=[sys.executable, "-m", "pytest", "tests/selected.py"]),
        )
        monkeypatch.setattr(
            scheduler, "validate_capability", lambda *a, **k: dict(template=template)
        )
    close = os.close

    def verify_close(fd):
        if fd in descriptors:
            assert (root / "quarantine.json").exists()
        return close(fd)

    monkeypatch.setattr(scheduler.os, "close", verify_close)
    with pytest.raises(RuntimeError, match="unjoined"):
        scheduler.run_command(command, leases)
    assert (root / "quarantine.json").exists()


@pytest.mark.parametrize(
    "xml",
    [
        "<testsuites><testsuite><testcase><skipped/></testcase></testsuite></testsuites>",
        "<testsuites><testsuite/></testsuites>",
        "<testsuites><testsuite><testcase><error/></testcase></testsuite></testsuites>",
    ],
)
def test_pg_exit_zero_cannot_pass_empty_or_skipped_junit(tmp_path, xml):
    from scripts.pipeline_pg import passed_cases

    path = tmp_path / "pg.xml"
    path.write_text(xml)
    with pytest.raises(ProtocolError, match="actual passes"):
        passed_cases(path)


def test_later_whole_parent_completion_consumed_without_mutating_packet(setup):
    admission.admit(setup["policy"])
    folder = Path(setup["policy"]["root"]) / "generations/T01"
    original = (folder / "packet.json").read_bytes()
    evidence = frozen(setup["root"] / "owner-evidence.json", dict(parent="T01", outcome="complete"))
    receipt = frozen(
        setup["root"] / "whole.json",
        dict(
            version=1,
            backlog_id="T01",
            status="done",
            coverage="whole_backlog",
            evidence=[evidence],
        ),
    )
    revised = json.loads(Path(setup["index"]["path"]).read_text())
    revised["completed"]["T01"] = receipt
    setup["policy"]["index"] = frozen(setup["root"] / "index-v2.json", revised)
    assert scheduler.generated_tick(setup["policy"])["T01"] == "done"
    assert (folder / "packet.json").read_bytes() == original
    setup["policy"]["index"] = frozen(setup["root"] / "index-v3.json", revised)
    assert scheduler.generated_tick(setup["policy"])["T01"] == "done"
    assert json.loads((folder / "external-completion.json").read_text())["receipt"] == receipt


def test_completion_cannot_erase_unresolved_child(setup):
    folder, _, _, _ = stage(setup)
    evidence = frozen(setup["root"] / "owner-evidence.json", dict(parent="T01"))
    receipt = frozen(
        setup["root"] / "whole.json",
        dict(
            version=1,
            backlog_id="T01",
            status="done",
            coverage="whole_backlog",
            evidence=[evidence],
        ),
    )
    revised = json.loads(Path(setup["index"]["path"]).read_text())
    revised["completed"]["T01"] = receipt
    setup["policy"]["index"] = frozen(setup["root"] / "index-v2.json", revised)
    assert scheduler.generated_tick(setup["policy"])["T01"].startswith("blocked:")
    assert not (folder / "external-completion.json").exists()


@pytest.mark.parametrize(
    "xml",
    [
        '<testsuites><testsuite skipped="1"><testcase name="x"/></testsuite></testsuites>',
        '<unknown><testcase name="x"/></unknown>',
    ],
)
def test_junit_suite_summary_cannot_hide_skip_or_unknown_format(tmp_path, xml):
    from scripts.pipeline_pg import passed_cases

    path = tmp_path / "junit.xml"
    path.write_text(xml)
    with pytest.raises(ProtocolError):
        passed_cases(path)


def test_pg_role_not_model_capability_and_author_cap_not_pg(setup):
    _, row, _, job = stage(setup)
    with pytest.raises(ProtocolError, match="unknown main worktree role"):
        capability.validate_capability(job, row / "ledger", host_pg=True)


def test_host_candidate_rejects_scope_file_changed_after_model_archive(setup):
    from scripts.pipeline_candidate import derive_candidate

    index = json.loads(Path(setup["index"]["path"]).read_text())
    contract_spec = index["contracts"]["T01"]["contract"]
    contract = json.loads(Path(contract_spec["path"]).read_text())
    contract["allowed_paths"].append("other.py")
    contract_spec.update(frozen(Path(contract_spec["path"]), contract))
    gate = index["contracts"]["T01"]["gates"][0]
    gate.update(
        frozen(
            Path(gate["path"]),
            dict(
                version=1,
                backlog_id="T01",
                contract_sha256=contract_spec["sha256"],
                decision="PASS",
            ),
        )
    )
    setup["index"].update(frozen(Path(setup["index"]["path"]), index))
    _, row, checkout, job = author_output(setup)
    (checkout / "other.py").write_text("value = 99\n")
    with pytest.raises(ProtocolError, match="source changed after model archive"):
        derive_candidate(job, row / "ledger")
    assert git(checkout, "rev-parse", "HEAD") == job.head
