"""Narrow, host-issued local-worktree capability; never a remote-effect grant."""

from __future__ import annotations

import fnmatch
import hashlib
import stat
from pathlib import Path

from scripts.pipeline_executor import run
from scripts.pipeline_protocol import decode, exact, require

FORBIDDEN = ("docs/architecture/", "config/harness/", ".codex/", ".github/")


def checked_file(spec):
    exact(spec, ("path", "sha256"))
    path = Path(spec["path"])
    require(path.is_absolute() and path.resolve() == path and path.is_file(), "frozen input path")
    require(not path.is_symlink(), "symlink frozen input")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == spec["sha256"], "frozen input drift")
    return raw


def allowed(path, patterns):
    return (
        path not in ("AGENTS.md", "harness.lock.yaml", "pyproject.toml", "uv.lock")
        and not path.startswith(FORBIDDEN)
        and any(fnmatch.fnmatchcase(path, p) for p in patterns)
    )


def source_paths(job, control, cap):
    """Validate worktree AND staged output; never accept an empty HEAD..HEAD shortcut."""
    checkout = Path(job.checkout)
    paths = set()
    for args in (
        ("diff", "--name-status", "--no-renames", job.head),
        ("diff", "--cached", "--name-status", "--no-renames", job.head),
    ):
        for row in run("git", *args, cwd=checkout).splitlines():
            status, name = row.split("\t", 1)
            require(
                status in ("A", "M") and allowed(name, cap["allowed_paths"]),
                "source output exceeds frozen contract",
            )
            paths.add(name)
    scratch = set()
    for marker in (control / "executions").glob(f"{job.task_id}-*/scratch.json"):
        path = Path(decode(marker.read_text())["path"])
        require(path.parent == checkout and path.resolve() == path, "unsafe host scratch")
        scratch.add(path.name)
    for name in run("git", "ls-files", "--others", "--exclude-standard", cwd=checkout).splitlines():
        if Path(name).parts[0] in scratch:
            continue  # Retained in the full attempt archive, never staged or accepted as source.
        require(allowed(name, cap["allowed_paths"]), "untracked output outside frozen source scope")
        paths.add(name)
    for name in paths:
        path = checkout / name
        require(
            path.resolve() == path
            and not path.is_symlink()
            and path.is_file()
            and stat.S_ISREG(path.lstat().st_mode)
            and path.lstat().st_nlink == 1,
            "source output not a canonical singly-linked regular file",
        )
    return sorted(paths)


def validate_capability(job, control, *, completed=False, host_pg=False):
    """Capability lives outside the writable checkout, inside its own host ledger."""
    path = Path(job.capability_file)
    require(path == control / "worktree-capability.json", "capability outside host ledger")
    cap = decode(checked_file(dict(path=str(path), sha256=job.capability_sha256)).decode())
    exact(
        cap,
        (
            "version",
            "backlog_id",
            "task_id",
            "checkout",
            "head",
            "stage",
            "allowed_paths",
            "authorization",
            "index",
            "contract",
            "template",
            "prompt_sha256",
        ),
    )
    require(cap["version"] == 1, "capability version")
    require(
        job.stage in (("pg",) if host_pg else ("implementation", "review")),
        "unknown main worktree role",
    )
    require(
        (cap["task_id"], cap["checkout"], cap["head"], cap["stage"])
        == (job.task_id, job.checkout, job.head, job.stage),
        "worktree capability binding",
    )
    auth = decode(checked_file(cap["authorization"]).decode())
    index = decode(checked_file(cap["index"]).decode())
    contract = decode(checked_file(cap["contract"]).decode())
    checked_file(cap["template"])
    rows = [t for t in auth["tasks"] if t["id"] == cap["backlog_id"]]
    require(len(rows) == 1 and rows[0]["authorized"] is True, "unauthorized local task")
    require(rows[0]["risk"] in ("low", "medium", "high"), "unknown task risk")
    gate = index["contracts"][cap["backlog_id"]]
    require(gate["contract"] == cap["contract"], "unindexed local contract")
    require(contract["scope_kind"] in ("implementation", "audit"), "owner-only local scope")
    from scripts.pipeline_admission import frozen_contract

    _item, _contract, template_spec, _template = frozen_contract(index, rows[0])
    require(template_spec == cap["template"], "unindexed closed template")
    require(contract["allowed_paths"] == cap["allowed_paths"], "local path grant drift")
    require(type(cap["allowed_paths"]) is list and bool(cap["allowed_paths"]), "empty local scope")
    checkout = Path(job.checkout)
    require(checkout.name == f"{cap['backlog_id']}-{job.stage}", "role worktrees must differ")
    require(
        Path(job.prompt_file) == control.parent / "prompt.txt"
        and hashlib.sha256(Path(job.prompt_file).read_bytes()).hexdigest() == cap["prompt_sha256"],
        "closed prompt binding drift",
    )
    require(
        checkout.resolve() == checkout and not control.resolve().is_relative_to(checkout),
        "unsafe local worktree",
    )
    require(
        run("git", "branch", "--show-current", cwd=checkout).startswith("throughput/"),
        "isolated throughput branch required",
    )
    require(
        not run("git", "worktree", "list", "--porcelain", cwd=checkout).startswith(
            "worktree " + str(checkout) + "\n"
        ),
        "primary checkout denied",
    )
    if completed:
        head = run("git", "rev-parse", "HEAD", cwd=checkout)
        require(head == job.head, "model changed HEAD; only host may derive candidate commit")
        if job.stage == "review":
            require(not run("git", "diff", "HEAD", "--", cwd=checkout), "review edited source")
            require(
                not run("git", "diff", "--cached", "HEAD", "--", cwd=checkout),
                "review changed index content",
            )
        source_paths(job, control, cap)
    return cap
