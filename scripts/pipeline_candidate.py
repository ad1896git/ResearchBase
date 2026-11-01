"""Host-derived local candidate commits, separate from immutable model receipts."""

from __future__ import annotations

import hashlib
import secrets
import tarfile
from pathlib import Path

from scripts.pipeline_admission import immutable
from scripts.pipeline_capability import source_paths, validate_capability
from scripts.pipeline_executor import run
from scripts.pipeline_protocol import StateStore, decode, require


def derive_candidate(job, control) -> dict:
    checkout = Path(job.checkout)
    cap = validate_capability(job, control)
    with StateStore(control, checkout) as store:
        task = store.state["tasks"][job.task_id]
        require(task["status"] == "done", "model execution has no accepted terminal receipt")
        result = control / task["result"]
        receipt_sha = hashlib.sha256(result.read_bytes()).hexdigest()
        attempt = task["attempt"]
    folder = control / "candidate"
    folder.mkdir(exist_ok=True)
    require(folder.resolve() == folder, "unsafe host candidate journal")
    intent_path, requested = folder / "intent.json", folder / "requested.json"
    head = run("git", "rev-parse", "HEAD", cwd=checkout)
    if intent_path.exists():
        intent = decode(intent_path.read_text())
        require(
            intent["author_receipt_sha256"] == receipt_sha and intent["base"] == job.head,
            "host derivation evidence drift",
        )
    else:
        validate_capability(job, control, completed=True)
        paths = source_paths(job, control, cap)
        require(paths, "no scoped implementation output; operator inspection required")
        output = control / "executions" / f"{job.task_id}-{attempt}"
        archive = output / "artifacts.tar"
        require(archive.is_file() and not archive.is_symlink(), "missing author source archive")
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        require(
            decode((output / "artifacts.json").read_text()) == dict(sha256=archive_sha),
            "author archive drift",
        )
        with tarfile.open(archive) as retained:
            for name in paths:
                member = retained.getmember(name)
                require(member.isfile(), "archived source not regular")
                stream = retained.extractfile(member)
                if stream is None:
                    raise ValueError("archived source absent")
                with stream:
                    require(
                        stream.read() == (checkout / name).read_bytes(),
                        "source changed after model archive",
                    )
        run("git", "add", "--", *paths, cwd=checkout)
        # Validate the actual staged tree, including any unexpected ambient index writes.
        source_paths(job, control, cap)
        tree = run("git", "write-tree", cwd=checkout)
        require(
            tree != run("git", "rev-parse", job.head + "^{tree}", cwd=checkout),
            "empty candidate tree",
        )
        intent = dict(
            id=secrets.token_hex(12),
            base=job.head,
            tree=tree,
            paths=paths,
            author_receipt_sha256=receipt_sha,
            capability_sha256=job.capability_sha256,
        )
        immutable(intent_path, intent)
    if head == job.head:
        require(not requested.exists(), "uncertain local commit outcome; never blindly repeat")
        require(run("git", "write-tree", cwd=checkout) == intent["tree"], "candidate index drift")
        immutable(requested, dict(intent_id=intent["id"]))
        run(
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "user.name=ResearchBase throughput host",
            "-c",
            "user.email=throughput-host@researchbase.invalid",
            "commit",
            "-m",
            f"Host-derived candidate {cap['backlog_id']} [throughput:{intent['id']}]",
            cwd=checkout,
        )
        head = run("git", "rev-parse", "HEAD", cwd=checkout)
    require(requested.is_file(), "unattributed candidate commit")
    parents = run("git", "rev-list", "--parents", "-n", "1", head, cwd=checkout).split()
    require(
        parents == [head, job.head]
        and run("git", "rev-parse", head + "^{tree}", cwd=checkout) == intent["tree"]
        and f"[throughput:{intent['id']}]"
        in run("git", "show", "-s", "--format=%B", head, cwd=checkout),
        "unexpected host candidate",
    )
    effect = dict(
        head=head,
        parent=job.head,
        tree=intent["tree"],
        intent_id=intent["id"],
        author_receipt_sha256=receipt_sha,
        capability_sha256=job.capability_sha256,
    )
    immutable(folder / "effect.json", effect)
    return effect
