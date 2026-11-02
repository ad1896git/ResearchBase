"""Closed-template admission from a frozen BACKLOG and gate evidence index."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import cast

from scripts.pipeline_capability import checked_file
from scripts.pipeline_executor import run
from scripts.pipeline_protocol import (
    ID,
    StateStore,
    atomic_write,
    commit,
    decode,
    encoded,
    exact,
    require,
)
from scripts.pipeline_safety import real_directory


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def immutable(path, value):
    require(not path.is_symlink(), "symlink admission journal")
    raw = encoded(value)
    if path.exists():
        require(path.read_bytes() == raw, "immutable admission drift")
    else:
        atomic_write(path, raw)


def sources(policy) -> tuple[list[dict], dict]:
    auth = decode(checked_file(policy["authorization"]).decode())
    index = decode(checked_file(policy["index"]).decode())
    exact(index, ("version", "contracts", "completed", "templates", "publications"))
    require(index["version"] == 1 and auth["version"] == 1, "admission input version")
    rows = auth["tasks"]
    require(type(rows) is list, "BACKLOG task list")
    typed = cast(list[dict], rows)
    require(len({r["id"] for r in typed}) == len(typed), "BACKLOG IDs")
    return typed, index


def completion(index, backlog_id):
    spec = index["completed"].get(backlog_id)
    if spec is None:
        return False
    receipt = decode(checked_file(spec).decode())
    exact(receipt, ("version", "backlog_id", "status", "evidence", "coverage"))
    require(
        receipt["version"] == 1
        and receipt["backlog_id"] == backlog_id
        and receipt["status"] == "done"
        and receipt["coverage"] == "whole_backlog"
        and receipt["evidence"],
        "completion receipt",
    )
    for evidence in receipt["evidence"]:
        checked_file(evidence)
    return True


def frozen_contract(index, row):
    item = index["contracts"].get(row["id"])
    require(item is not None, "contract not frozen/indexed")
    exact(item, ("contract", "template", "gates"))
    contract = decode(checked_file(item["contract"]).decode())
    exact(
        contract,
        ("version", "backlog_id", "scope_kind", "frozen", "allowed_paths", "specification"),
    )
    require(
        contract["version"] == 1
        and contract["frozen"] is True
        and contract["backlog_id"] == row["id"],
        "unfrozen contract",
    )
    require(contract["scope_kind"] in ("implementation", "audit"), "owner-only scope")
    specification = checked_file(contract["specification"])
    require(1 <= len(specification) <= 128000, "bounded frozen execution specification required")
    require(type(contract["allowed_paths"]) is list and contract["allowed_paths"], "path scope")
    require(item["gates"], "missing frozen gate evidence")
    for spec in item["gates"]:
        gate = decode(checked_file(spec).decode())
        exact(gate, ("version", "backlog_id", "contract_sha256", "decision"))
        require(
            gate
            == dict(
                version=1,
                backlog_id=row["id"],
                contract_sha256=item["contract"]["sha256"],
                decision="PASS",
            ),
            "gate not PASS on frozen contract",
        )
    template_spec = index["templates"][item["template"]]
    template = decode(checked_file(template_spec).decode())
    exact(template, ("version", "implementation_prompt", "review_prompt", "pg_argv"))
    require(template["version"] == 1, "closed template version")
    for name in ("implementation_prompt", "review_prompt"):
        require(
            type(template[name]) is str and 1 <= len(template[name]) <= 32000,
            "bounded closed prompt",
        )
    argv = template["pg_argv"]
    require(
        type(argv) is list
        and (
            not argv
            or (
                len(argv) >= 4
                and argv[:3] == [sys.executable, "-m", "pytest"]
                and all(
                    type(a) is str and a.startswith("tests/") and ".." not in a for a in argv[3:]
                )
            )
        ),
        "PG template must use pinned Python pytest files, no shell/options",
    )
    return item, contract, template_spec, template


def base_head(policy):
    repository = policy["repository"]
    require(
        repository.lower() in ("ad1896git/researchbase", "ad1896git/researchbase-pipeline-sandbox"),
        "source repository",
    )
    branch = policy["base_ref"]
    require(
        branch == "main"
        or (repository.lower().endswith("-sandbox") and branch.startswith("pipeline-test/")),
        "base scope",
    )
    row = json.loads(run("gh", "api", f"repos/{repository}/git/ref/heads/{branch}", timeout=15))
    head = row["object"]["sha"]
    commit(head)
    source = Path(policy["source_checkout"])
    require(source.is_absolute() and source.resolve() == source, "source checkout path")
    origin = run("git", "remote", "get-url", "origin", cwd=source).lower().removesuffix(".git")
    require(origin == "https://github.com/" + repository.lower(), "source origin")
    run("git", "fetch", "origin", branch, cwd=source, timeout=30)
    require(run("git", "rev-parse", "FETCH_HEAD", cwd=source) == head, "fresh source drift")
    return head


def admit(policy):
    """Caller owns the short wakeup lease. No task-specific job packs are supplied."""
    rows, index = sources(policy)
    root = Path(policy["root"])
    real_directory(root / "generations")
    journal = root / "admitted-packets.json"
    admitted = decode(journal.read_text()) if journal.exists() else {}
    for name, saved in admitted.items():
        path = root / "generations" / name / "packet.json"
        require(
            path.is_file()
            and not path.is_symlink()
            and path.resolve() == path
            and digest(path.read_bytes()) == saved,
            "admitted packet lost/drifted; never recreate forgotten history",
        )
    statuses = {}
    for row in rows:
        name = row["id"]
        require(type(name) is str and ID.fullmatch(name), "BACKLOG identifier")
        folder = root / "generations" / name
        require(folder.resolve() == folder and not folder.is_symlink(), "unsafe generation path")
        if (folder / "packet.json").exists():
            admitted[name] = digest((folder / "packet.json").read_bytes())
            statuses[name] = "admitted"
            continue
        try:
            require(row["authorized"] is True, "not authorized")
            require(row["risk"] in ("low", "medium", "high"), "unknown risk")
            require(name not in ("M01", "D01", "F01", "R02"), "owner-only BACKLOG task")
            if completion(index, name):
                statuses[name] = "previously_done"
                continue
            require(
                all(completion(index, dep) for dep in row.get("depends_on", [])),
                "dependencies lack verified completion",
            )
            item, contract, template_spec, template = frozen_contract(index, row)
            # The packet is entirely host-derived from immutable evidence, never model output.
            real_directory(folder)
            head = base_head(policy)
            packet = dict(
                version=1,
                backlog_id=name,
                risk=row["risk"],
                head=head,
                authorization=policy["authorization"],
                index=policy["index"],
                contract=item["contract"],
                template=template_spec,
                repository=policy["repository"],
                base_ref=policy["base_ref"],
                source_checkout=policy["source_checkout"],
                allowed_paths=contract["allowed_paths"],
                stages=(["implementation"] + (["pg"] if template["pg_argv"] else []) + ["review"]),
                goal=row.get("goal", ""),
                acceptance=row.get("acceptance", ""),
            )
            immutable(folder / "packet.json", packet)
            immutable(folder / "progress.json", dict(stage="implementation", status="ready"))
            admitted[name] = digest((folder / "packet.json").read_bytes())
            statuses[name] = "admitted"
        except Exception as exc:
            statuses[name] = f"held: {type(exc).__name__}: {exc}"
    atomic_write(root / "admission-status.json", encoded(statuses))
    atomic_write(journal, encoded(admitted))
    return statuses


def prepare_stage(policy, folder, packet, stage):
    """Create one independent stage worktree, preserving any incomplete admission."""
    row = folder / stage
    real_directory(row)
    checkout = Path(policy["worktrees"]) / f"{packet['backlog_id']}-{stage}"
    require(checkout.is_absolute() and checkout.resolve() == checkout, "worktree path")
    head = packet["head"]
    if stage != "implementation":
        author = folder / "implementation" / "ledger"
        with StateStore(
            author, Path(policy["worktrees"]) / f"{packet['backlog_id']}-implementation"
        ) as store:
            task = store.state["tasks"]["work"]
            require(task["status"] == "done", "author receipt not done")
            receipt = decode((author / task["result"]).read_text())
        from scripts.pipeline_candidate import derive_candidate
        from scripts.pipeline_worker import WorkerJob

        author_job = WorkerJob(**decode((folder / "implementation/job.json").read_text()))
        require(receipt["receipt"]["commit"] == packet["head"], "model receipt HEAD changed")
        head = derive_candidate(author_job, author)["head"]
        commit(head)
    binding = dict(checkout=str(checkout), head=head, stage=stage, backlog_id=packet["backlog_id"])
    immutable(row / "target.json", binding)
    if not checkout.exists():
        require(not (row / "worktree-requested.json").exists(), "uncertain worktree creation")
        immutable(row / "worktree-requested.json", binding)
        real_directory(checkout.parent)
        run(
            "git",
            "worktree",
            "add",
            "-b",
            f"throughput/{packet['backlog_id']}-{stage}",
            str(checkout),
            head,
            cwd=Path(packet["source_checkout"]),
            timeout=30,
        )
    require(
        run("git", "rev-parse", "HEAD", cwd=checkout) == head
        or (row / "ledger/initialized").exists(),
        "worktree initial head drift",
    )
    ledger = row / "ledger"
    if not (ledger / "initialized").exists():
        require(not ledger.exists(), "incomplete ledger initialization; do not reset")
        with StateStore(ledger, checkout, create=True) as store:
            store.add("work")
    template = decode(checked_file(packet["template"]).decode())
    prompt = (
        template["review_prompt" if stage == "review" else "implementation_prompt"]
        + f"\nDo not create a local .venv or install environments. Use {sys.executable} "
        "with PYTHONPATH=$PWD/src for local checks. "
        "Heavy PostgreSQL verification is a separate host phase. "
        "Do not stage or commit: the host derives a separately journaled "
        "candidate after validation. "
        "Review runs read-only: report source-file hashes as evidence and findings in notes; "
        "do not write a review artifact into either worktree.\n"
        + "\nFrozen authorized task:\n"
        + json.dumps(packet, ensure_ascii=False)
    )
    contract = decode(checked_file(packet["contract"]).decode())
    prompt += (
        "\nFrozen execution specification:\n" + checked_file(contract["specification"]).decode()
    )
    immutable(row / "prompt.json", dict(prompt=prompt))
    prompt_path = row / "prompt.txt"
    if not prompt_path.exists():
        atomic_write(prompt_path, prompt.encode())
    require(prompt_path.read_text() == prompt, "prompt drift")
    cap = dict(
        version=1,
        backlog_id=packet["backlog_id"],
        task_id="work",
        checkout=str(checkout),
        head=head,
        stage=stage,
        allowed_paths=packet["allowed_paths"],
        prompt_sha256=digest(prompt.encode()),
        **{k: packet[k] for k in ("authorization", "index", "contract", "template")},
    )
    cap_path = ledger / "worktree-capability.json"
    immutable(cap_path, cap)
    job = dict(
        task_id="work",
        key=f"throughput:{packet['backlog_id']}:{stage}",
        checkout=str(checkout),
        prompt_file=str(prompt_path),
        head=head,
        base=packet["head"],
        stage=stage,
        attempt_limit=2,
        capability_file=str(cap_path),
        capability_sha256=digest(cap_path.read_bytes()),
    )
    immutable(row / "job.json", job)
    return row, checkout, template
