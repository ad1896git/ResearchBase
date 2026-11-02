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
from pathlib import Path
from typing import Any

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
        require(path.resolve() == path, "input ancestor changed")
        visit(path)
        require(path.resolve() == path, "input ancestor changed")
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


def plan(root, attempt=0):
    require(root.is_dir() and root.resolve() == root, "root missing/noncanonical")
    info = root.stat()
    require(
        info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
        "private owned root required",
    )
    inventory([root], strict=True)  # No initial symlink/hardlink alias, even in unreferenced files.
    manifest = json.loads((root / "manifest.json").read_text())
    exact(
        manifest,
        (
            "version",
            "python",
            "online_inputs",
            "script",
            "script_sha256",
            "bindings",
            "plists",
            "timeout",
            "deployment",
        ),
    )
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
    readonly = (str(runtime), str(python), *executable_dirs)
    for item in manifest["bindings"]:
        validate_paths(json.loads(beneath(item, root).read_text()), writable, readonly)
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


def profile(root):
    # All descendants inherit Seatbelt. No writable inherited files or IPC broker.
    return (
        "(version 1)(allow default)(deny file-write*)"
        "(allow file-write* (subpath " + json.dumps(str(root), ensure_ascii=False) + "))"
        "(deny file-write* (literal " + json.dumps(str(root / ".deny-canary")) + "))"
        "(deny network*)(deny mach-lookup)"
    )


def child(root: Path, argv: list[str], timeout: int) -> dict[str, Any]:
    require(sys.platform == "darwin" and SANDBOX.is_file(), "OS write isolation unavailable")
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
    result = json.loads(prior.read_text())
    require(
        result["status"] == "blocked"
        and result["possible_online_write"] is False
        and result.get("quarantined", True) is False,
        "passed or possible online write attempt cannot be retried",
    )
    return len(names)


def run(root, correction=None):
    attempt = next_attempt(root, correction)
    manifest, inputs, script, plist_hashes = plan(root, attempt)
    before = inventory(inputs)
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
    write_json(
        area,
        "intent.json",
        dict(
            attempt=attempt,
            inputs=protected,
            before=before,
            writable_root=str(writable),
            profile=profile(writable),
        ),
    )
    phases = []
    failure = None
    quarantined = False
    try:
        probe = capability_probe(root, Path(manifest["python"]), writable)
        write_json(area, "kernel-probe.json", probe)
        for phase in ("normal", "rollback"):
            require(
                root.resolve() == root
                and (root.stat().st_dev, root.stat().st_ino) == root_identity,
                "root identity changed",
            )
            require(sha(script) == manifest["script_sha256"], "scenario source changed")
            protected_before = inventory([evidence], strict=True)
            if manifest["deployment"] is None:
                argv = [manifest["python"], "-B", str(script), "--phase", phase]
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
            phases.append(dict(phase=phase, **observed))
            current = inventory(inputs)
            require(current == before, "online inventory changed; STOP operation, owner required")
            require(
                not observed["timed_out"]
                and observed["exit_code"] == (0 if phase == "normal" else 23),
                "scenario failed/expected injected rollback not observed",
            )
    except (SafetyError, OSError, ValueError, subprocess.SubprocessError) as error:
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
        possible_online_write=not unchanged,
        quarantined=quarantined,
        live_unchanged=unchanged,
        failure=failure,
        before=before,
        after=after,
        phases=phases,
        plist_hashes=plist_hashes,
        mode="isolated_rehearsal",
        deployment="NOT_EXECUTED",
        adapter="deployment" if manifest["deployment"] else "generic",
        correction_budget="maximum3 explicit corrections; no automatic retry",
    )
    write_json(area, "result.json", result)
    return 0 if result["status"] == "pass" else 2


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


def bootstrap(root, correction):
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
    plan(root, attempt)  # Pure first-write rejection of all declared payload paths.
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
        "_outer",
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
    for name in ("run", "_outer"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--correction-of")
    args = parser.parse_args(argv)
    try:
        root = canonical(args.root)
        if args.command == "_outer":
            confined(root)
            require(
                os.environ.get("RB_PREFLIGHT_ROOT_ID")
                == f"{root.stat().st_dev}:{root.stat().st_ino}",
                "bootstrap root identity mismatch",
            )
            CONFINED = True
            return run(root, args.correction_of)
        return bootstrap(root, args.correction_of)
    except (
        SafetyError,
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
