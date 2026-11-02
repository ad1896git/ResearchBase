"""Explicit macOS kernel-isolated rehearsal; never deploys or dispatches a service."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.pipeline_protocol import ProtocolError, decode
from scripts.pipeline_safety import SafetyError
from scripts.pipeline_sessions import stop_group

SANDBOX = Path("/usr/bin/sandbox-exec")
CONFINED = False
MAX_FILES = 100000
MAX_BYTES = 1024 * 1024 * 1024


class UnknownChildren(SafetyError):
    pass


def joined(value):
    if not value:
        raise UnknownChildren("unknown descendants; root quarantined")


def require(value, message):
    if not value:
        raise SafetyError(message)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), "unknown or missing fields")


def canonical(value):
    require(type(value) is str and value.startswith("/"), "absolute path required")
    path = Path(value)
    require(str(path) == value and path.resolve() == path, "noncanonical/symlink path")
    require(not any(ord(c) < 32 for c in value), "control character in path")
    return path


def signature(info):
    return {
        key: getattr(info, "st_" + key)
        for key in ("dev", "ino", "mode", "uid", "gid", "nlink", "size", "mtime_ns", "ctime_ns")
    }


def inventory(paths, *, strict=False):
    """Read every entry, including logs/empty dirs. No lock, excludes or writes."""
    result = {}
    budget = [0, 0]

    def visit(path: Path, parent: int | None = None, name: str = ""):
        before = (
            os.stat(name, dir_fd=parent, follow_symlinks=False)
            if parent is not None
            else path.lstat()
        )
        if stat.S_ISLNK(before.st_mode) and not strict:
            target = os.readlink(name, dir_fd=parent) if parent is not None else os.readlink(path)
            named = (
                os.stat(name, dir_fd=parent, follow_symlinks=False)
                if parent is not None
                else path.lstat()
            )
            require(signature(before) == signature(named), "symlink changed during scan")
            result[str(path)] = {
                **signature(before),
                "kind": "symlink",
                "target": target,
                "target_sha256": hashlib.sha256(os.fsencode(target)).hexdigest(),
            }
            budget[0] += 1
            require(budget[0] <= MAX_FILES, "inventory entry budget exceeded")
            return
        require(stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode), "unsafe input type")
        require(
            not strict or not stat.S_ISREG(before.st_mode) or before.st_nlink == 1,
            "hardlinked input",
        )
        fd = os.open(
            name if parent is not None else path,
            os.O_RDONLY | os.O_NOFOLLOW | (os.O_DIRECTORY if stat.S_ISDIR(before.st_mode) else 0),
            dir_fd=parent,
        )
        try:
            require(signature(os.fstat(fd)) == signature(before), "input changed on open")
            row = signature(before)
            budget[0] += 1
            require(budget[0] <= MAX_FILES, "inventory entry budget exceeded")
            if stat.S_ISDIR(before.st_mode):
                names = sorted(os.listdir(fd))
                row["kind"] = "directory"
                row["children"] = names
                for child in names:
                    visit(path / child, fd, child)
                require(sorted(os.listdir(fd)) == names, "directory membership changed")
            else:
                row["kind"] = "file"
                digest = hashlib.sha256()
                while block := os.read(fd, 65536):
                    budget[1] += len(block)
                    require(budget[1] <= MAX_BYTES, "inventory byte budget exceeded")
                    digest.update(block)
                row["sha256"] = digest.hexdigest()
            named = (
                os.stat(name, dir_fd=parent, follow_symlinks=False)
                if parent is not None
                else path.lstat()
            )
            require(
                signature(before) == signature(os.fstat(fd)) == signature(named),
                "input changed during scan",
            )
            result[str(path)] = row
        finally:
            os.close(fd)

    for path in paths:
        boundary = path.parent if not strict and path.is_symlink() else path
        require(boundary.resolve() == boundary, "input ancestor changed")
        visit(path)
        require(boundary.resolve() == boundary, "input ancestor changed")
    return result


def beneath(value, root):
    path = canonical(value)
    require(path.is_relative_to(root), "writable path escapes root")
    return path


def validate_paths(value, root, readonly=()):
    """Bindings may contain scalar data; every absolute path must be root-local."""
    if type(value) is str:
        candidate = value.split("=", 1)[-1]
        if candidate.startswith("/") and candidate not in readonly:
            beneath(candidate, root)
    elif type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, "binding key")
            validate_paths(item, root, readonly)
    elif type(value) is list:
        for item in value:
            validate_paths(item, root, readonly)
    else:
        require(value is None or type(value) in (int, bool, float), "binding value")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_plist(path, root, python, runtime=None, executable_dirs=()):
    raw = path.read_bytes()
    value = plistlib.loads(raw)
    allowed = {
        "Label",
        "ProgramArguments",
        "WorkingDirectory",
        "StandardOutPath",
        "StandardErrorPath",
        "EnvironmentVariables",
        "StartInterval",
        "RunAtLoad",
    }
    require(type(value) is dict and set(value) <= allowed, "unsupported plist fields")
    require(
        {"Label", "ProgramArguments", "StandardOutPath", "StandardErrorPath"} <= set(value),
        "incomplete plist paths",
    )
    argv: Any = value["ProgramArguments"]
    require(type(argv) is list and len(argv) >= 2 and argv[0] == str(python), "plist interpreter")
    for item in argv[1:]:
        require(type(item) is str and item, "plist argv")
        validate_paths(item, root)
    require(type(value["Label"]) is str and value["Label"], "plist service identity")
    for key in ("WorkingDirectory", "StandardOutPath", "StandardErrorPath"):
        if key in value and not (key == "WorkingDirectory" and value[key] == str(runtime)):
            beneath(value[key], root)
    if "StartInterval" in value:
        require(
            type(value["StartInterval"]) is int and value["StartInterval"] == 300, "plist interval"
        )
    if "RunAtLoad" in value:
        require(value["RunAtLoad"] is True, "plist RunAtLoad")
    env: dict[str, Any] = value.get("EnvironmentVariables", {})
    require(
        type(env) is dict
        and set(env) <= {"HOME", "TMPDIR", "TMPPREFIX", "PYTHONPATH", "CODEX_HOME", "PATH"},
        "plist environment",
    )
    for key, item in env.items():
        if key == "PYTHONPATH":
            require(item == str(runtime), "readonly runtime import root")
        elif key == "PATH":
            require(item == ":".join(executable_dirs), "readonly executable search path")
        else:
            beneath(item, root)
    return hashlib.sha256(raw).hexdigest()


def interpreter_aliases(path):
    current = Path("/")
    pending = list(path.parts[1:])
    found = set()
    followed = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        candidate = current / part
        if candidate.is_symlink():
            followed += 1
            found.add(str(candidate))
            require(followed <= 40, "interpreter alias bound")
            target = Path(os.readlink(candidate))
            if target.is_absolute():
                current = Path("/")
                pending = list(target.parts[1:]) + pending
            else:
                pending = list(target.parts) + pending
        else:
            current = candidate
    return sorted(found)


def interpreter_closure(
    specs: list[dict[str, Any]], inputs, python, prior_runtime=None, write_root=None
):
    expected = {"current": python}
    if prior_runtime is not None:
        expected["prior"] = prior_runtime / ".venv/bin/python3"
    require(type(specs) is list and len(specs) == len(expected), "interpreter closure roles")
    seen = set()
    for spec in specs:
        exact(
            spec,
            (
                "role",
                "executable",
                "resolved_executable",
                "executable_sha256",
                "base_runtime",
                "path_aliases",
            ),
        )
        role = spec["role"]
        require(type(role) is str and role in expected and role not in seen, "interpreter role")
        seen.add(role)
        lexical = expected[role]
        require(spec["executable"] == str(lexical), "interpreter lexical path changed")
        resolved = lexical.resolve(strict=True)
        require(
            spec["resolved_executable"] == str(resolved)
            and resolved.is_file()
            and sha(resolved) == spec["executable_sha256"],
            "resolved interpreter digest drift",
        )
        base = canonical(spec["base_runtime"])
        require(base.is_dir() and resolved.is_relative_to(base), "interpreter base runtime")
        require(
            any(base == p or base.is_relative_to(p) for p in inputs),
            "base runtime outside snapshot closure",
        )
        runtime = lexical.parents[2]
        require(
            any(runtime == p or runtime.is_relative_to(p) for p in inputs),
            "lexical runtime outside snapshot closure",
        )
        cfg = lexical.parents[1] / "pyvenv.cfg"
        require(cfg.is_file() and not cfg.is_symlink(), "venv configuration missing/aliased")
        homes = [
            line.split("=", 1)[1].strip()
            for line in cfg.read_text().splitlines()
            if line.split("=", 1)[0].strip() == "home" and "=" in line
        ]
        require(
            len(homes) == 1
            and Path(homes[0]).is_absolute()
            and Path(homes[0]).resolve().parent == base,
            "venv base runtime mismatch",
        )
        aliases = sorted(set(interpreter_aliases(lexical) + interpreter_aliases(Path(homes[0]))))
        require(spec["path_aliases"] == aliases, "interpreter alias closure mismatch")
        for name in aliases:
            alias = Path(name)
            require(
                alias.parent.resolve() == alias.parent and alias.is_symlink(),
                "interpreter alias changed",
            )
            require(
                write_root is None
                or (not alias.is_relative_to(write_root) and not write_root.is_relative_to(alias)),
                "interpreter alias/writeRoot overlap",
            )
            if not any(alias == p or alias.is_relative_to(p) for p in inputs):
                inputs.append(alias)
        if role == "current":
            require(Path(sys.base_prefix).resolve() == base, "current loaded base prefix mismatch")
    return specs


def plan(root, attempt=0):
    require(root.is_dir() and root.resolve() == root, "root missing/noncanonical")
    info = root.stat()
    require(
        info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
        "private owned root required",
    )
    inventory([root], strict=True)  # No initial symlink/hardlink alias, even in unreferenced files.
    manifest = proof_json((root / "manifest.json").read_text())
    exact(manifest, MANIFEST_KEYS)
    require(
        type(manifest["version"]) is int and manifest["version"] == 1,
        "unsupported manifest version",
    )
    python = Path(manifest["python"])
    require(
        python.is_absolute()
        and str(python) == manifest["python"]
        and python.parent.resolve() == python.parent
        and python.is_file(),
        "unsafe interpreter",
    )
    require(
        str(python) == sys.executable
        and python.parent.name == "bin"
        and python.parent.parent.name == ".venv"
        and sys.version_info[:2] == (3, 12),
        "fixed project venv Python3.12 required",
    )
    require(
        type(manifest["online_inputs"]) is list and manifest["online_inputs"],
        "online inputs required",
    )
    inputs = [canonical(item) for item in manifest["online_inputs"]]
    require(len(set(inputs)) == len(inputs), "duplicate input")
    for index, path in enumerate(inputs):
        require(
            not path.is_relative_to(root) and not root.is_relative_to(path), "input/root overlap"
        )
        require(
            not any(
                path.is_relative_to(other) or other.is_relative_to(path) for other in inputs[:index]
            ),
            "overlapping inputs",
        )
    script = beneath(manifest["script"], root)
    require(script.is_file() and sha(script) == manifest["script_sha256"], "script digest mismatch")
    require(type(manifest["timeout"]) is int and 1 <= manifest["timeout"] <= 300, "timeout bound")
    require(
        type(manifest["bindings"]) is list
        and type(manifest["plists"]) is list
        and manifest["plists"],
        "bindings/plists required",
    )
    writable = root / "payload" / f"attempt-{attempt}"
    runtime = python.parents[2]
    executable_dirs = []
    if manifest["deployment"] is not None:
        from scripts.pipeline_preflight_deploy import validate_deployment

        executable_dirs = validate_deployment(
            manifest["deployment"], root, writable, inputs, python
        )
    interpreter_closure(
        manifest["interpreter_inputs"],
        inputs,
        python,
        Path(manifest["deployment"]["prior_runtime"]) if manifest["deployment"] else None,
        write_root=root,
    )
    readonly = (str(runtime), str(python), *executable_dirs)
    for item in manifest["bindings"]:
        validate_paths(proof_json(beneath(item, root).read_text()), writable, readonly)
    # Both old and replacement are explicit; no last-argv guessing or live mapping.
    labels = set()
    plist_hashes = {}
    for item in manifest["plists"]:
        exact(item, ("role", "path", "sha256", "original_path", "original_sha256", "path_mapping"))
        require(item["role"] in ("old", "replacement") and item["role"] not in labels, "plist role")
        labels.add(item["role"])
        path = beneath(item["path"], root)
        row_runtime = runtime
        if item["role"] == "old" and manifest["deployment"] is not None:
            row_runtime = Path(manifest["deployment"]["prior_runtime"])
        actual = checked_plist(
            path, writable, row_runtime / ".venv/bin/python3", row_runtime, executable_dirs
        )
        require(
            actual == item["sha256"]
            and type(item["original_sha256"]) is str
            and re.fullmatch("[0-9a-f]{64}", item["original_sha256"]),
            "plist hash",
        )
        original = beneath(item["original_path"], root)
        require(sha(original) == item["original_sha256"], "original plist hash")
        mapping = item["path_mapping"]
        require(type(mapping) is dict, "plist path mapping")
        for old, new in mapping.items():
            canonical(old)
            beneath(new, writable)

        def mapped(value, mapping=mapping):
            if type(value) is str:
                return mapping.get(value, value)
            if type(value) is list:
                return [mapped(v) for v in value]
            if type(value) is dict:
                return {k: mapped(v) for k, v in value.items()}
            return value

        require(
            mapped(plistlib.loads(original.read_bytes())) == plistlib.loads(path.read_bytes()),
            "unproven original/mapped plist correspondence",
        )
        plist_hashes[item["role"]] = dict(
            mapped_sha256=actual, original_sha256=item["original_sha256"], path_mapping=mapping
        )
    require(labels == {"old", "replacement"}, "both plist roles required")
    return manifest, inputs, script, plist_hashes


def null_identity():
    # Owner-approved immutable character sink only, with no namespace privilege.
    path = Path("/dev/null")
    before = path.lstat()
    require(
        stat.S_ISCHR(before.st_mode)
        and before.st_uid == 0
        and before.st_gid == 0
        and before.st_nlink == 1
        and os.major(before.st_rdev) == 3
        and os.minor(before.st_rdev) == 2,
        "unexpected /dev/null device identity",
    )
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        held = os.fstat(fd)
        after = path.lstat()
        keys = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_rdev")
        require(
            tuple(getattr(before, k) for k in keys)
            == tuple(getattr(held, k) for k in keys)
            == tuple(getattr(after, k) for k in keys),
            "/dev/null changed during validation",
        )
        return {k[3:]: getattr(held, k) for k in keys}
    finally:
        os.close(fd)


def profile(root):
    # All descendants inherit Seatbelt. No writable inherited files or IPC broker.
    return (
        "(version 1)(allow default)(deny file-write*)"
        "(allow file-write* (subpath " + json.dumps(str(root), ensure_ascii=False) + "))"
        "(deny file-write* (literal " + json.dumps(str(root / ".deny-canary")) + "))"
        '(allow file-write-data (literal "/dev/null"))'
        "(deny network*)(deny mach-lookup)"
    )


def child(root: Path, argv: list[str], timeout: int) -> dict[str, Any]:
    require(sys.platform == "darwin" and SANDBOX.is_file(), "OS write isolation unavailable")
    null_identity()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root / "home"),
        "TMPDIR": str(root / "tmp"),
        "TMPPREFIX": str(root / "tmp/prefix"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(root),
        "LC_ALL": "C",
    }
    with open("/dev/null", "rb") as null:
        command = argv if CONFINED else [str(SANDBOX), "-p", profile(root), *argv]
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdin=null,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stopped = stop_group(process.pid, process.poll)
        joined(stopped)
        stdout, stderr = process.communicate(timeout=3)
    finally:
        stopped = stop_group(process.pid, process.poll)
    joined(stopped)
    require(len(stdout) + len(stderr) <= 8 * 1024 * 1024, "child output bound")
    return dict(
        exit_code=process.returncode,
        timed_out=timed_out,
        descendants_stopped=True,
        stdout=stdout.decode("utf-8", "replace"),
        stderr=stderr.decode("utf-8", "replace"),
    )


def capability_probe(root, python, writable):
    denied = root / ".deny-canary"
    before = denied.read_bytes()
    program = (
        "import pathlib,subprocess,sys; p=pathlib.Path(sys.argv[1]); "
        "r=subprocess.run(['/bin/sh','-c','printf broken > \"$1\"','sh',str(p)]); "
        "sys.exit(0 if r.returncode != 0 and p.read_bytes()==b'protected-canary' else 9)"
    )
    negative = child(writable, [str(python), "-B", "-c", program, str(denied)], 10)
    require(
        negative["exit_code"] == 0
        and denied.read_bytes() == before
        and "Operation not permitted" in negative["stderr"],
        "kernel deny probe failed",
    )
    positive = child(
        writable,
        [str(python), "-B", "-c", 'from pathlib import Path;Path("positive").write_text("ok")'],
        10,
    )
    require(
        positive["exit_code"] == 0 and (writable / "positive").read_text() == "ok",
        "kernel allow probe failed",
    )
    return dict(deny=negative, allow=positive)


def write_json(target, name, value):
    # Parent writes only root/evidence, never online; refuse child-created aliases.
    require(target.resolve() == target and target.is_dir(), "evidence directory changed")
    path = target / name
    require(not path.exists() and not path.is_symlink(), "evidence collision")
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        directory = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return hashlib.sha256(raw).hexdigest()


def next_attempt(root, correction):
    evidence = root / "evidence"
    if not evidence.exists():
        require(correction is None, "no prior attempt for correction")
        return 0
    require(evidence.is_dir() and evidence.resolve() == evidence, "unsafe evidence directory")
    names = sorted(p.name for p in evidence.iterdir())
    require(
        names and names == [f"attempt-{i}" for i in range(len(names))], "incomplete attempt history"
    )
    require(len(names) <= 3, "three corrections exhausted; STOP")
    prior = evidence / names[-1] / "result.json"
    require(prior.is_file() and not prior.is_symlink(), "uncertain prior attempt; reconcile only")
    require(
        correction is not None and sha(prior) == correction, "explicit exact prior result required"
    )
    result = proof_json(prior.read_text())
    require(
        result["status"] == "blocked"
        and result["possible_online_write"] is False
        and result.get("quarantined", True) is False,
        "passed or possible online write attempt cannot be retried",
    )
    return len(names)


def capture_roles(root, manifest):
    """Root-local pinned preparation roles, checked before reading online inputs."""
    require(manifest["deployment"] is None, "capture requires generic readonly payload")
    path = str(root / "capture.json")
    require(path in manifest["bindings"], "capture authorization must be protected input")
    value = proof_json(read_artifact(str(root), "capture.json"))
    exact(value, ("version", "script_sha256", "context", "roles", "sources"))
    require(type(value["version"]) is int and value["version"] == 1, "capture version")
    require(value["script_sha256"] == manifest["script_sha256"], "capture script binding")
    sources = value["sources"]
    exact(
        sources,
        ("deploy.py", "manifest.py", "snapshot_inventory.py", "rollback.py", "capture-manifest.py"),
    )
    require(
        manifest["script"] == str(root / "capture-manifest.py"), "closed capture entry required"
    )
    for relative, digest in sources.items():
        require(
            hashlib.sha256(read_artifact(str(root), relative)).hexdigest() == digest,
            "capture source closure drift",
        )
    context = value["context"]
    exact(
        context,
        (
            "release_head",
            "tool_merge_head",
            "validation_pr",
            "validation_head",
            "validation_base",
            "validation_run",
            "queue_sha256",
            "index_sha256",
        ),
    )
    for key in ("release_head", "tool_merge_head", "validation_head", "validation_base"):
        require(
            type(context[key]) is str and re.fullmatch("[0-9a-f]{40}", context[key]),
            "pending capture head",
        )
    for key in ("queue_sha256", "index_sha256"):
        require(
            type(context[key]) is str and re.fullmatch("[0-9a-f]{64}", context[key]),
            "pending capture digest",
        )
    for key in ("validation_pr", "validation_run"):
        require(type(context[key]) is int and context[key] > 0, "pending capture witness")
    roles = value["roles"]
    exact(roles, ("index-activation-review", "validation-admission-review"))
    for role, pin in roles.items():
        exact(pin, ("path", "sha256"))
        require(pin["path"] == role + ".json", "capture role path")
        require(str(root / pin["path"]) in manifest["bindings"], "unprotected capture role")
        raw = read_artifact(str(root), pin["path"])
        require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "capture role digest")
        receipt = proof_json(raw)
        exact(receipt, ("version", "role", "verdict", "findings", "context"))
        require(
            type(receipt["version"]) is int
            and receipt["version"] == 1
            and receipt["role"] == role
            and receipt["verdict"] == "PASS"
            and receipt["findings"] == []
            and receipt["context"] == context,
            "capture role not PASS/exact context",
        )
    return value


def run(root, correction=None, *, capture=False):
    attempt = next_attempt(root, correction)
    if capture:
        capture_roles(root, proof_json(read_artifact(str(root), "manifest.json")))
    manifest, inputs, script, plist_hashes = plan(root, attempt)
    if capture:
        capture_roles(root, manifest)
    before = inventory(inputs)
    interpreter_closure(
        manifest["interpreter_inputs"],
        inputs,
        Path(manifest["python"]),
        Path(manifest["deployment"]["prior_runtime"]) if manifest["deployment"] else None,
        write_root=root,
    )
    root_identity = (root.stat().st_dev, root.stat().st_ino)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700, exist_ok=True)
    area = evidence / f"attempt-{attempt}"
    area.mkdir(mode=0o700)
    writable = root / "payload" / f"attempt-{attempt}"
    writable.parent.mkdir(mode=0o700, exist_ok=True)
    writable.mkdir(mode=0o700, exist_ok=False)
    for name in ("home", "tmp"):
        (writable / name).mkdir(mode=0o700)
    protected = {
        "manifest.json": (root / "manifest.json").read_bytes().hex(),
        "script": script.read_bytes().hex(),
    }
    for path in manifest["bindings"] + [
        v[k] for v in manifest["plists"] for k in ("path", "original_path")
    ]:
        protected[path] = Path(path).read_bytes().hex()
    intent_sha256 = write_json(
        area,
        "intent.json",
        dict(
            attempt=attempt,
            inputs=protected,
            before=before,
            null_device=null_identity(),
            effective_write_root=str(root),
            payload_workdir=str(writable),
            profile=profile(root),
        ),
    )
    phases = []
    stage_proofs = []
    failure = None
    quarantined = False
    try:
        probe = capability_probe(root, Path(manifest["python"]), writable)
        write_json(area, "kernel-probe.json", probe)
        for phase in ("capture",) if capture else ("normal", "rollback"):
            require(
                root.resolve() == root
                and (root.stat().st_dev, root.stat().st_ino) == root_identity,
                "root identity changed",
            )
            require(sha(script) == manifest["script_sha256"], "scenario source changed")
            interpreter_closure(
                manifest["interpreter_inputs"],
                inputs,
                Path(manifest["python"]),
                Path(manifest["deployment"]["prior_runtime"]) if manifest["deployment"] else None,
                write_root=root,
            )
            protected_before = inventory([evidence], strict=True)
            if manifest["deployment"] is None:
                argv = [manifest["python"], "-B", str(script)]
                if not capture:
                    argv += ["--phase", phase]
            else:
                adapter = Path(__file__).with_name("pipeline_preflight_deploy.py").resolve()
                argv = [
                    manifest["python"],
                    "-B",
                    str(adapter),
                    "--root",
                    str(root),
                    "--attempt",
                    str(attempt),
                    "--phase",
                    phase,
                ]
            observed = child(writable, argv, manifest["timeout"])
            require(
                inventory([evidence], strict=True) == protected_before,
                "protected attempt evidence changed",
            )
            for path in manifest["bindings"] + [
                v[k] for v in manifest["plists"] for k in ("path", "original_path")
            ]:
                require(Path(path).read_bytes().hex() == protected[path], "protected input changed")
            require(
                (root / "manifest.json").read_bytes().hex() == protected["manifest.json"]
                and script.read_bytes().hex() == protected["script"],
                "protected manifest/source changed",
            )
            interpreter_closure(
                manifest["interpreter_inputs"],
                inputs,
                Path(manifest["python"]),
                Path(manifest["deployment"]["prior_runtime"]) if manifest["deployment"] else None,
                write_root=root,
            )
            if capture:
                capture_roles(root, manifest)
            phases.append(dict(phase=phase, **observed))
            current = inventory(inputs)
            require(current == before, "online inventory changed; STOP operation, owner required")
            require(
                not observed["timed_out"]
                and observed["exit_code"] == (0 if phase in ("normal", "capture") else 23),
                "capture failed"
                if capture
                else "scenario failed/expected injected rollback not observed",
            )
            if manifest["deployment"] is not None:
                relative = f"payload/attempt-{attempt}/{phase}/adapter-result.json"
                data = read_artifact(str(root), relative)
                exact(proof_json(data), STAGE_KEYS)
                stage_proofs.append(
                    dict(phase=phase, path=relative, sha256=hashlib.sha256(data).hexdigest())
                )
    except (SafetyError, ProtocolError, OSError, ValueError, subprocess.SubprocessError) as error:
        failure = type(error).__name__ + ": " + str(error)
        quarantined = isinstance(error, UnknownChildren)
    try:
        after = inventory(inputs)
        unchanged = after == before
    except (SafetyError, OSError) as error:
        after = {"inventory_error": str(error)}
        unchanged = False
    result = dict(
        version=1,
        status="pass" if failure is None and unchanged else "blocked",
        attempt=attempt,
        null_device=null_identity(),
        possible_online_write=not unchanged,
        quarantined=quarantined,
        live_unchanged=unchanged,
        failure=failure,
        before=before,
        after=after,
        phases=phases,
        intent_sha256=intent_sha256,
        stage_proofs=stage_proofs,
        plist_hashes=plist_hashes,
        mode="readonly_capture" if capture else "isolated_rehearsal",
        deployment="NOT_EXECUTED",
        adapter="capture" if capture else ("deployment" if manifest["deployment"] else "generic"),
        correction_budget="maximum3 explicit corrections; no automatic retry",
    )
    exact(result, RESULT_KEYS)
    write_json(area, "result.json", result)
    return 0 if result["status"] == "pass" else 2


RESULT_KEYS = (
    "version",
    "status",
    "attempt",
    "null_device",
    "possible_online_write",
    "quarantined",
    "live_unchanged",
    "failure",
    "before",
    "after",
    "phases",
    "intent_sha256",
    "stage_proofs",
    "plist_hashes",
    "mode",
    "deployment",
    "adapter",
    "correction_budget",
)
INTENT_KEYS = (
    "attempt",
    "inputs",
    "before",
    "null_device",
    "effective_write_root",
    "payload_workdir",
    "profile",
)
MANIFEST_KEYS = (
    "version",
    "python",
    "online_inputs",
    "script",
    "script_sha256",
    "bindings",
    "plists",
    "timeout",
    "deployment",
    "interpreter_inputs",
)
STAGE_KEYS = (
    "success",
    "phase",
    "payload_sha256",
    "same_payload_bytes",
    "baseline",
    "required_feature54",
    "launchctl",
    "baseline_git",
    "clock",
    "calls",
    "mapping",
)


def proof_json(raw):
    # Existing protocol decoder has an intentional1MiB report limit. Full-tree
    # snapshots are larger; keep that old boundary unchanged and use the same
    # duplicate/nonfinite policy with this artifact's explicit128MiB bound.
    if type(raw) is bytes:
        require(len(raw) <= 128 * 1024 * 1024, "artifact size budget")
        raw = raw.decode("utf-8")
    require(type(raw) is str and len(raw.encode()) <= 128 * 1024 * 1024, "artifact JSON budget")
    if len(raw.encode()) <= 1024 * 1024:
        return decode(raw)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    return json.loads(
        raw, object_pairs_hook=pairs, parse_constant=lambda _: require(False, "nonfinite JSON")
    )


def hex_digest(value):
    require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "SHA256 syntax")
    return value


def lexical_absolute(value):
    require(
        type(value) is str
        and value.startswith("/")
        and str(Path(value)) == value
        and not any(ord(c) < 32 for c in value),
        "absolute lexical path required",
    )
    return Path(value)


def relative_artifact(value):
    require(
        type(value) is str
        and value
        and not value.startswith("/")
        and all(p not in ("", ".", "..") for p in value.split("/")),
        "relative artifact required",
    )
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationContext:
    """Caller supplies independently trusted pins, not authority inferred from JSON."""

    root: str
    attempt: int
    result_sha256: str
    manifest_sha256: str
    payload_sha256: str
    release_head: str
    python: str
    expected_bindings: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        # All scalar validation precedes any filesystem access, including root lookup.
        for value in (self.result_sha256, self.manifest_sha256, self.payload_sha256):
            hex_digest(value)
        require(
            type(self.release_head) is str and re.fullmatch("[0-9a-f]{40}", self.release_head),
            "release head syntax",
        )
        require(type(self.attempt) is int and 0 <= self.attempt <= 3, "attempt syntax")
        lexical_absolute(self.root)
        lexical_absolute(self.python)
        require(type(self.expected_bindings) is tuple, "binding pins must be immutable")
        names = []
        for item in self.expected_bindings:
            require(type(item) is tuple and len(item) == 2, "closed binding pin")
            relative_artifact(item[0])
            hex_digest(item[1])
            names.append(item[0])
        require(len(names) == len(set(names)), "duplicate binding pin")


def read_artifact(root_name, relative):
    """Root-local descriptor traversal; no commands, writes, locks or online reads."""
    root = lexical_absolute(root_name)
    relative_artifact(relative)
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in root.parts[1:]:
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child_fd
        info = os.fstat(fd)
        require(
            info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
            "private proof root required",
        )
        pieces = relative.split("/")
        for part in pieces[:-1]:
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child_fd
        before = os.stat(pieces[-1], dir_fd=fd, follow_symlinks=False)
        require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
            "regular unaliased artifact required",
        )
        leaf = os.open(pieces[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            require(signature(os.fstat(leaf)) == signature(before), "artifact changed on open")
            data = bytearray()
            while part := os.read(leaf, 65536):
                data.extend(part)
                require(len(data) <= 128 * 1024 * 1024, "artifact size budget")
            named = os.stat(pieces[-1], dir_fd=fd, follow_symlinks=False)
            require(
                signature(before) == signature(os.fstat(leaf)) == signature(named),
                "artifact changed during read",
            )
            return bytes(data)
        finally:
            os.close(leaf)
    finally:
        os.close(fd)


def snapshot_proof(snapshot: dict[str, dict[str, Any]], manifest: dict[str, Any], root: Path):
    require(
        type(snapshot) is dict and snapshot and len(snapshot) <= MAX_FILES,
        "complete snapshot required",
    )
    require(
        type(manifest["online_inputs"]) is list and manifest["online_inputs"],
        "online input declarations",
    )
    roots = [lexical_absolute(p) for p in manifest["online_inputs"]]
    for spec in manifest["interpreter_inputs"]:
        exact(
            spec,
            (
                "role",
                "executable",
                "resolved_executable",
                "executable_sha256",
                "base_runtime",
                "path_aliases",
            ),
        )
        hex_digest(spec["executable_sha256"])
        require(type(spec["path_aliases"]) is list, "alias declarations")
        roots += [lexical_absolute(p) for p in spec["path_aliases"]]
    require(
        all(not p.is_relative_to(root) and not root.is_relative_to(p) for p in roots),
        "proof root/online overlap",
    )
    require(all(str(p) in snapshot for p in roots), "missing declared snapshot root")
    roots = [p for p in roots if not any(other != p and p.is_relative_to(other) for other in roots)]
    metadata = ("dev", "ino", "mode", "uid", "gid", "nlink", "size", "mtime_ns", "ctime_ns")
    total = 0
    for name, row in snapshot.items():
        path = lexical_absolute(name)
        require(any(path == p or path.is_relative_to(p) for p in roots), "undeclared snapshot path")
        require(
            type(row) is dict and row.get("kind") in ("file", "directory", "symlink"),
            "snapshot row",
        )
        kind = row["kind"]
        extra = (
            ("sha256",)
            if kind == "file"
            else (("children",) if kind == "directory" else ("target", "target_sha256"))
        )
        exact(row, (*metadata, "kind", *extra))
        require(all(type(row[k]) is int for k in metadata), "snapshot metadata types")
        require(
            all(row[k] >= 0 for k in metadata if k not in ("mtime_ns", "ctime_ns")),
            "snapshot metadata range",
        )
        if kind == "file":
            require(stat.S_ISREG(row["mode"]), "file mode")
            hex_digest(row["sha256"])
            total += row["size"]
        elif kind == "directory":
            require(stat.S_ISDIR(row["mode"]) and type(row["children"]) is list, "directory row")
            children: list[str] = row["children"]
            require(
                all(
                    type(c) is str and c not in ("", ".", "..") and "/" not in c
                    for c in row["children"]
                ),
                "directory names",
            )
            require(sorted(set(row["children"])) == row["children"], "directory ordering")
            require(
                all(str(path / c) in snapshot for c in children),
                "incomplete directory snapshot",
            )
        else:
            require(stat.S_ISLNK(row["mode"]) and type(row["target"]) is str, "symlink row")
            require(
                hashlib.sha256(os.fsencode(row["target"])).hexdigest() == row["target_sha256"],
                "symlink text digest",
            )
        require(path in roots or str(path.parent) in snapshot, "missing snapshot ancestor")
        if str(path.parent) in snapshot:
            parent = snapshot[str(path.parent)]
            require(
                parent["kind"] == "directory" and path.name in parent["children"],
                "snapshot parent membership",
            )
    require(total <= MAX_BYTES, "snapshot byte budget")


def recorded_resolution(path, snapshot):
    current = Path("/")
    pending = list(path.parts[1:])
    followed = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        candidate = current / part
        row = snapshot.get(str(candidate))
        if row is not None and row["kind"] == "symlink":
            followed += 1
            require(followed <= 40, "recorded alias loop")
            target = Path(row["target"])
            if target.is_absolute():
                current = Path("/")
                pending = list(target.parts[1:]) + pending
            else:
                pending = list(target.parts) + pending
        else:
            current = candidate
    return current


def verify_result(context: VerificationContext):
    """Verify historical Root proof bytes only; not current host/source attestation."""
    require(type(context) is VerificationContext, "typed verification context required")
    context.__post_init__()
    root = Path(context.root)
    require(context.python == sys.executable, "verification interpreter mismatch")

    def document(relative, expected) -> Any:
        data = read_artifact(context.root, relative)
        require(hashlib.sha256(data).hexdigest() == hex_digest(expected), "artifact SHA mismatch")
        return proof_json(data)

    result = document(f"evidence/attempt-{context.attempt}/result.json", context.result_sha256)
    exact(result, RESULT_KEYS)
    require(
        type(result["version"]) is int
        and result["version"] == 1
        and result["status"] == "pass"
        and result["adapter"] == "deployment"
        and result["mode"] == "isolated_rehearsal"
        and result["deployment"] == "NOT_EXECUTED",
        "successful deployment rehearsal required",
    )
    require(
        type(result["attempt"]) is int and result["attempt"] == context.attempt,
        "result attempt mismatch",
    )
    require(
        result["live_unchanged"] is True
        and result["possible_online_write"] is False
        and result["quarantined"] is False
        and result["failure"] is None
        and result["before"] == result["after"],
        "online change/failure/unknown proof",
    )
    require(
        result["correction_budget"] == "maximum3 explicit corrections; no automatic retry",
        "correction policy",
    )
    manifest = document("manifest.json", context.manifest_sha256)
    exact(manifest, MANIFEST_KEYS)
    require(
        type(manifest["version"]) is int
        and manifest["version"] == 1
        and manifest["python"] == context.python
        and manifest["script_sha256"] == context.payload_sha256,
        "manifest payload/interpreter mismatch",
    )
    model = manifest["deployment"]
    exact(
        model,
        (
            "version",
            "head",
            "required_feature54",
            "stamp",
            "mappings",
            "rewrite_json",
            "prior_plist",
            "prior_runtime",
            "path_aliases",
            "executable_dirs",
            "codex_version",
            "runtime",
        ),
    )
    require(
        type(model["version"]) is int
        and model["version"] == 1
        and model["head"] == context.release_head
        and model["runtime"] == str(Path(context.python).parents[2])
        and model["required_feature54"] == "7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2",
        "release head/base mismatch",
    )
    snapshot_proof(result["before"], manifest, root)
    roles = {v["role"]: v for v in manifest["interpreter_inputs"]}
    require(
        len(roles) == len(manifest["interpreter_inputs"]) == 2
        and set(roles) == {"current", "prior"},
        "interpreter proof roles",
    )
    for role, spec in roles.items():
        expected_python = (
            context.python
            if role == "current"
            else str(Path(model["prior_runtime"]) / ".venv/bin/python3")
        )
        executable = lexical_absolute(spec["resolved_executable"])
        base = lexical_absolute(spec["base_runtime"])
        require(
            spec["executable"] == expected_python
            and executable.is_relative_to(base)
            and recorded_resolution(Path(expected_python), result["before"]) == executable,
            "recorded interpreter path mismatch",
        )
        binary = result["before"].get(str(executable))
        require(
            binary is not None
            and binary["kind"] == "file"
            and binary["sha256"] == spec["executable_sha256"],
            "recorded interpreter binary mismatch",
        )
        require(
            str(base) in result["before"] and result["before"][str(base)]["kind"] == "directory",
            "base runtime closure absent",
        )
    intent = document(f"evidence/attempt-{context.attempt}/intent.json", result["intent_sha256"])
    exact(intent, INTENT_KEYS)
    require(
        type(intent["attempt"]) is int
        and intent["attempt"] == context.attempt
        and intent["before"] == result["before"]
        and intent["effective_write_root"] == context.root
        and intent["payload_workdir"] == str(root / "payload" / f"attempt-{context.attempt}")
        and intent["profile"] == profile(root)
        and intent["null_device"] == result["null_device"],
        "intent/root/profile binding",
    )
    device = result["null_device"]
    exact(device, ("dev", "ino", "mode", "uid", "gid", "nlink", "rdev"))
    require(
        all(type(v) is int for v in device.values())
        and stat.S_ISCHR(device["mode"])
        and device["uid"] == device["gid"] == 0
        and device["nlink"] == 1
        and os.major(device["rdev"]) == 3
        and os.minor(device["rdev"]) == 2,
        "null device proof",
    )
    protected = intent["inputs"]
    require(type(protected) is dict, "protected inputs")
    script_path = lexical_absolute(manifest["script"])
    require(script_path.is_relative_to(root), "payload artifact escapes root")
    require(
        type(manifest["bindings"]) is list
        and type(manifest["plists"]) is list
        and len(manifest["plists"]) == 2,
        "input declarations",
    )
    paths = manifest["bindings"] + [
        p[k] for p in manifest["plists"] for k in ("path", "original_path")
    ]
    require(set(protected) == {"manifest.json", "script", *paths}, "protected input coverage")
    for name, value in protected.items():
        require(
            type(value) is str and len(value) % 2 == 0 and re.fullmatch("[0-9a-f]*", value),
            "protected byte encoding",
        )
        data = bytes.fromhex(value)
        if name == "manifest.json":
            relative, expected = "manifest.json", context.manifest_sha256
        elif name == "script":
            relative, expected = str(script_path.relative_to(root)), context.payload_sha256
        else:
            absolute = lexical_absolute(name)
            require(absolute.is_relative_to(root), "binding artifact escapes root")
            relative, expected = str(absolute.relative_to(root)), hashlib.sha256(data).hexdigest()
        require(
            hashlib.sha256(data).hexdigest() == expected
            and read_artifact(context.root, relative) == data,
            "protected input bytes changed",
        )
    for relative, expected in context.expected_bindings:
        name = str(root / relative)
        require(
            name in manifest["bindings"]
            and name in protected
            and hashlib.sha256(bytes.fromhex(protected[name])).hexdigest() == expected,
            "expected binding commitment missing/changed",
        )
    require(
        type(result["phases"]) is list
        and len(result["phases"]) == 2
        and type(result["stage_proofs"]) is list
        and len(result["stage_proofs"]) == 2,
        "incomplete phases",
    )
    for phase, wanted, row, proof in zip(
        ("normal", "rollback"), (0, 23), result["phases"], result["stage_proofs"], strict=True
    ):
        exact(row, ("phase", "exit_code", "timed_out", "descendants_stopped", "stdout", "stderr"))
        require(
            row["phase"] == phase
            and type(row["exit_code"]) is int
            and row["exit_code"] == wanted
            and row["timed_out"] is False
            and row["descendants_stopped"] is True
            and type(row["stdout"]) is str
            and type(row["stderr"]) is str,
            "phase terminal proof",
        )
        exact(proof, ("phase", "path", "sha256"))
        require(
            proof["phase"] == phase
            and proof["path"] == f"payload/attempt-{context.attempt}/{phase}/adapter-result.json",
            "stage location",
        )
        stage = document(proof["path"], proof["sha256"])
        exact(stage, STAGE_KEYS)
        require(
            stage["success"] is True
            and stage["phase"] == phase
            and stage["same_payload_bytes"] is True
            and stage["payload_sha256"] == context.payload_sha256
            and stage["baseline"] == context.release_head
            and stage["required_feature54"] == model["required_feature54"]
            and stage["launchctl"] == stage["clock"] == "SIMULATED_ONLY",
            "same-byte stage/release mismatch",
        )
        require(
            type(stage["calls"]) is list
            and type(stage["mapping"]) is list
            and all(type(c) is list and all(type(a) is str for a in c) for c in stage["calls"]),
            "closed stage command trace",
        )
        plist = str(
            root
            / "payload"
            / f"attempt-{context.attempt}"
            / "fixture"
            / relative_artifact(model["prior_plist"])
        )
        for action in ("bootstrap", "bootout"):
            require(
                ["launchctl", action, f"gui/{os.getuid()}", plist] in stage["calls"],
                "incomplete simulated service trace",
            )
        facts: list[dict[str, Any]] = stage["baseline_git"]
        require(type(facts) is list and len(facts) == 2, "native baseline facts")
        for fact in facts:
            exact(fact, ("argv", "exit_code", "stdout", "stderr"))
            require(
                type(fact["exit_code"]) is int
                and fact["exit_code"] == 0
                and type(fact["stdout"]) is str
                and type(fact["stderr"]) is str,
                "native baseline outcome",
            )
        require(
            facts[0]["argv"] == ["git", "-C", model["runtime"], "rev-parse", "HEAD"]
            and facts[0]["stdout"].strip() == context.release_head
            and facts[1]["argv"]
            == [
                "git",
                "-C",
                model["runtime"],
                "merge-base",
                "--is-ancestor",
                model["required_feature54"],
                context.release_head,
            ],
            "native exact head/base facts",
        )
    require(
        type(result["plist_hashes"]) is dict
        and set(result["plist_hashes"]) == {"old", "replacement"},
        "plist proof roles",
    )
    require(
        {p["role"] for p in manifest["plists"]} == {"old", "replacement"}, "manifest plist roles"
    )
    for p in manifest["plists"]:
        exact(p, ("role", "path", "sha256", "original_path", "original_sha256", "path_mapping"))
        require(
            result["plist_hashes"][p["role"]]
            == dict(
                mapped_sha256=p["sha256"],
                original_sha256=p["original_sha256"],
                path_mapping=p["path_mapping"],
            ),
            "plist hashes/mapping mismatch",
        )
    return dict(
        status="verified",
        root=context.root,
        attempt=context.attempt,
        result_sha256=context.result_sha256,
        manifest_sha256=context.manifest_sha256,
        payload_sha256=context.payload_sha256,
        release_head=context.release_head,
        python=context.python,
        current_online_state="NOT_RESCANNED",
        authority="CALLER_TRUSTED_CONTEXT_AND_EXECUTION_SOURCE_REQUIRED",
        deployment="NOT_EXECUTED",
    )


def confined(root):
    require(sys.platform == "darwin", "OS isolation unsupported")
    library = ctypes.CDLL("/usr/lib/system/libsystem_sandbox.dylib")
    check = library.sandbox_check
    check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    check.restype = ctypes.c_int
    require(
        check(
            os.getpid(), b"file-write-data", 1, ctypes.c_char_p(os.fsencode(root / "manifest.json"))
        )
        == 0
        and check(
            os.getpid(), b"file-write-data", 1, ctypes.c_char_p(os.fsencode(root / ".deny-canary"))
        )
        == 1,
        "orchestrator is not kernel-confined to root",
    )


def bootstrap(root, correction, *, capture=False):
    require(sys.platform == "darwin" and SANDBOX.is_file(), "OS write isolation unavailable")
    require(
        root.is_dir()
        and root.resolve() == root
        and root.stat().st_uid == os.getuid()
        and stat.S_IMODE(root.stat().st_mode) == 0o700,
        "private canonical root required",
    )
    # No inherited regular stdout/stderr: an already-open online FD would bypass
    # resource-acquisition filtering. All outer/child streams are fresh pipes.
    require(
        all(not stat.S_ISREG(os.fstat(fd).st_mode) for fd in (1, 2)),
        "regular inherited output descriptor forbidden",
    )
    null_identity()
    original_root = (root.stat().st_dev, root.stat().st_ino)
    env = {
        "RB_PREFLIGHT_ROOT_ID": f"{original_root[0]}:{original_root[1]}",
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "HOME": str(root),
        "TMPDIR": str(root),
        "LC_ALL": "C",
    }
    attempt = next_attempt(root, correction)
    if capture:
        capture_roles(root, proof_json(read_artifact(str(root), "manifest.json")))
    prepared = plan(root, attempt)  # Pure first-write rejection of all declared payload paths.
    if capture:
        capture_roles(root, prepared[0])
    canary = root / ".deny-canary"
    if not canary.exists():
        fd = os.open(canary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"protected-canary")
            stream.flush()
            os.fsync(stream.fileno())
    require(
        not canary.is_symlink()
        and canary.stat().st_nlink == 1
        and canary.read_bytes() == b"protected-canary",
        "canary identity",
    )
    require(
        (root.stat().st_dev, root.stat().st_ino) == original_root, "root replaced during bootstrap"
    )
    argv = [
        str(SANDBOX),
        "-p",
        profile(root),
        sys.executable,
        "-B",
        "-m",
        "scripts.pipeline_preflight",
        "_capture_outer" if capture else "_outer",
        "--root",
        str(root),
    ]
    if correction is not None:
        argv += ["--correction-of", correction]
    with open("/dev/null", "rb") as null:
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=env,
            close_fds=True,
            stdin=null,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    try:
        stdout, stderr = process.communicate(timeout=700)
    except subprocess.TimeoutExpired:
        require(stop_group(process.pid, process.poll), "unknown outer descendants; STOP")
        raise SafetyError("outer timeout; preserve root and reconcile") from None
    require(stop_group(process.pid, process.poll), "unknown outer descendants; STOP")
    sys.stdout.buffer.write(stdout)
    sys.stderr.buffer.write(stderr)
    return process.returncode


def main(argv=None):
    global CONFINED
    # Validate inherited output FDs even before argparse could print an error.
    if any(stat.S_ISREG(os.fstat(fd).st_mode) for fd in (1, 2)):
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "_outer", "capture", "_capture_outer"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--correction-of")
    verify = commands.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--attempt", required=True, type=int)
    for flag in ("result-sha256", "manifest-sha256", "payload-sha256", "release-head", "python"):
        verify.add_argument("--" + flag, required=True)
    verify.add_argument("--binding", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            pins = tuple(tuple(value.rsplit("=", 1)) for value in args.binding)
            context = VerificationContext(
                root=args.root,
                attempt=args.attempt,
                result_sha256=args.result_sha256,
                manifest_sha256=args.manifest_sha256,
                payload_sha256=args.payload_sha256,
                release_head=args.release_head,
                python=args.python,
                expected_bindings=pins,
            )
            print(json.dumps(verify_result(context), sort_keys=True))
            return 0
        root = canonical(args.root)
        if args.command in ("_outer", "_capture_outer"):
            confined(root)
            null_identity()
            require(
                os.environ.get("RB_PREFLIGHT_ROOT_ID")
                == f"{root.stat().st_dev}:{root.stat().st_ino}",
                "bootstrap root identity mismatch",
            )
            CONFINED = True
            return run(root, args.correction_of, capture=args.command == "_capture_outer")
        return bootstrap(root, args.correction_of, capture=args.command == "capture")
    except (
        SafetyError,
        ProtocolError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ) as error:
        print(json.dumps(dict(status="blocked", reason=str(error), deployment="NOT_EXECUTED")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
