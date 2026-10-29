"""Controlled startup against a protected, frozen temporary installation."""

import hashlib
import json
import marshal
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from researchbase.foundation import bearing_installation as bi
from researchbase.foundation.bearing_installation import (
    InstallationError,
    Limits,
    _artifact_digest,
    _bounds,
    _Observation,
    _parse_manifest,
)

BOOTSTRAP = r"""import sys
from pathlib import Path
base = Path(__file__).parent.parent
source = base / "source"
lib = base / "runtime" / "lib" / ("python%d.%d" % sys.version_info[:2])
sys.path[:] = [str(source), str(lib), str(lib / "lib-dynload")]
import os, pickle
from researchbase.foundation import bearing_installation as bi

records = base / "records"
scenario = sys.argv[1]
kw = dict(approval_path=records / "approval.json",
          manifest_path=records / "manifest.json", namespace="test")
if scenario == "prepare-negative":
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert sys.argv[2] in str(exc), str(exc)
        print("REJECT prepare", exc)
    else:
        raise AssertionError("bad installation accepted")
    sys.exit(0)
if scenario in ("path-hook", "path-traversal"):
    if scenario == "path-hook":
        sys.meta_path.append(object())
        expected = "unsupported import hooks"
    else:
        sys.path.append(str(source) + "/../records")
        expected = "invalid import path"
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert expected in str(exc), str(exc)
        print("REJECT", scenario, exc)
    else:
        raise AssertionError("unsafe import state accepted")
    sys.exit(0)
if scenario == "stale":
    target = source / "researchbase/agent_runtime/domain/research_task.py"
    current = target.read_bytes()
    target.write_bytes(current + b"\nSTALE_STARTUP_MARKER = True\n")
    import researchbase.agent_runtime.domain.research_task
    target.write_bytes(current)
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert "preloaded non-bootstrap module" in str(exc), str(exc)
        print("REJECT stale-loaded", exc)
    else:
        raise AssertionError("stale module accepted")
    sys.exit(0)
if scenario == "preloaded-stdlib":
    import fractions
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert "preloaded non-bootstrap module" in str(exc), str(exc)
        print("REJECT non-bootstrap stdlib", exc)
    else:
        raise AssertionError("non-bootstrap stdlib accepted")
    sys.exit(0)
if scenario == "shadow-stdlib":
    # A real inventoried runtime file with an allowlisted stdlib name must not
    # become bootstrap code merely because the import path is under lib.
    sys.path.insert(0, str(lib / "vendor"))
    del sys.modules["pickle"]
    import pickle
    assert pickle.SHADOW_BOOTSTRAP_MARKER is True
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert "preloaded non-bootstrap module: pickle" in str(exc), str(exc)
        print("REJECT shadow stdlib", exc)
    else:
        raise AssertionError("shadow stdlib accepted as bootstrap")
    sys.exit(0)
if scenario == "fifo":
    original = os.open
    record = records / "manifest.json"
    def racing_open(path, flags, *args):
        if path == record:
            record.rename(records / "manifest.saved")
            os.mkfifo(record, 0o600)
        return original(path, flags, *args)
    os.open = racing_open
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert "file changed before read" in str(exc), str(exc)
        print("REJECT fifo race", exc)
    else:
        raise AssertionError("fifo accepted")
    finally:
        os.open = original
        record.unlink()
        (records / "manifest.saved").rename(record)
    sys.exit(0)
if scenario == "expiry":
    from datetime import datetime, UTC, timedelta
    real_datetime = bi.datetime
    real_inventory = bi._inventory
    state = [False]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            t = real_datetime.now(tz)
            return t + timedelta(days=2) if state[0] else t
    def inventory(*args):
        result = real_inventory(*args)
        state[0] = True
        return result
    bi.datetime = Clock
    bi._inventory = inventory
    try:
        bi.prepare_installation(**kw)
    except bi.InstallationError as exc:
        assert "operator record expired" in str(exc), str(exc)
        print("REJECT expiry during inventory", exc)
    else:
        raise AssertionError("expired context issued")
    sys.exit(0)
print("BEFORE", sorted(n for n in sys.modules if n.startswith("researchbase")), flush=True)
print("BOOTSTRAP MODULES", sorted(sys.modules), flush=True)
prepared = bi.prepare_installation(**kw)
try:
    bi.PreparedInstallation()
except TypeError:
    pass
else:
    raise AssertionError("public context constructor")
try:
    pickle.dumps(prepared)
except TypeError:
    pass
else:
    raise AssertionError("serialized context")
print("PREPARED", sorted(n for n in sys.modules if n.startswith("researchbase")), flush=True)
from researchbase.agent_runtime.domain.bearing_evaluation import evaluate
print("IMPORTED", sorted(n for n in sys.modules if n.startswith("researchbase")), flush=True)
if scenario == "final-negative":
    variant = sys.argv[2]
    module = sys.modules[evaluate.__module__]
    target = source / "researchbase/foundation/errors.py"
    original = target.read_bytes()
    if variant == "file identity mismatch":
        target.write_bytes(original + b"\n")
    elif variant == "callable code mismatch":
        evaluate.__code__ = (lambda: None).__code__
    elif variant == "callable binding mismatch":
        module.evaluate = lambda: None
    elif variant == "unapproved module origin":
        module.__file__ = str(records / "wrong.py")
    elif variant == "bootstrap import state changed":
        sys.path.append(str(records))
    try:
        bi.verify_installation(prepared=prepared, fixed_callable=evaluate)
    except bi.InstallationError as exc:
        assert variant in str(exc), (variant, str(exc))
        print("REJECT final", exc)
    else:
        raise AssertionError("bad final state accepted")
    finally:
        if variant == "file identity mismatch":
            target.write_bytes(original)
    sys.exit(0)
if scenario in ("final-expiry", "final-time"):
    from datetime import datetime, timedelta
    original_inventory = bi._inventory
    original_datetime = bi.datetime
    original_time = bi.time.monotonic
    expired = [False]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            current = original_datetime.now(tz)
            return current + timedelta(days=2) if expired[0] else current
    def inventory(*args):
        value = original_inventory(*args)
        if scenario == "final-expiry":
            expired[0] = True
        return value
    bi.datetime = Clock
    bi._inventory = inventory
    if scenario == "final-time":
        real_unexpired = bi._unexpired
        calls = [0]
        def unexpired(approval):
            real_unexpired(approval)
            calls[0] += 1
        bi._unexpired = unexpired
        bi.time.monotonic = lambda: original_time() + (121 if calls[0] >= 3 else 0)
    try:
        bi.verify_installation(prepared=prepared, fixed_callable=evaluate)
    except bi.InstallationError as exc:
        expected = ("operator record expired" if scenario == "final-expiry"
                    else "verification timeout")
        assert expected in str(exc), str(exc)
        print("REJECT", scenario, exc)
    else:
        raise AssertionError("expired or overrun proof issued")
    sys.exit(0)
proof = bi.verify_installation(prepared=prepared, fixed_callable=evaluate)
print("POSITIVE hash_reads=%d hash_bytes=%d elapsed=%.6f" % proof.measurements, flush=True)
try:
    bi.verify_installation(prepared=None, fixed_callable=evaluate)
except bi.InstallationError as exc:
    assert "invalid prepared context" in str(exc), str(exc)
else:
    raise AssertionError("raw callable accepted")
try:
    bi.VerifiedInstallation()
except TypeError:
    pass
else:
    raise AssertionError("public proof constructor")
try:
    bi.verify_installation(prepared=prepared, fixed_callable=evaluate)
except bi.InstallationError as exc:
    assert "consumed" in str(exc), str(exc)
else:
    raise AssertionError("context reused")
try:
    pickle.dumps(proof)
except TypeError:
    pass
else:
    raise AssertionError("serialized proof")
"""


def _identity(path: Path) -> dict[str, object]:
    s = path.stat()
    return {
        "device": s.st_dev,
        "inode": s.st_ino,
        "size": s.st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "owner_uid": s.st_uid,
        "mode": stat.S_IMODE(s.st_mode),
    }


def _root(label: str, kind: str, path: Path) -> dict[str, object]:
    s = path.stat()
    files = []
    for current, _, names in os.walk(path):
        for name in names:
            p = Path(current) / name
            suffix = p.suffix
            file_kind = (
                "source"
                if suffix == ".py"
                else "bytecode"
                if suffix == ".pyc"
                else "native"
                if suffix in (".so", ".dylib")
                else "runtime"
            )
            files.append(
                {
                    "relative_path": p.relative_to(path).as_posix(),
                    "kind": file_kind,
                    "identity": _identity(p),
                }
            )
    return {
        "label": label,
        "kind": kind,
        "path": str(path),
        "device": s.st_dev,
        "inode": s.st_ino,
        "owner_uid": s.st_uid,
        "mode": stat.S_IMODE(s.st_mode),
        "files": files,
    }


def _checked_prefix(path: Path) -> None:
    for part in (path, *path.parents):
        info = os.lstat(part)
        assert stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid())
        assert not info.st_mode & 0o7022


@pytest.fixture(scope="module")
def installation():
    project = Path(__file__).resolve().parents[3]
    prefix = project / "tmp" / "installation465-test"
    prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
    _checked_prefix(prefix)
    base = Path(tempfile.mkdtemp(prefix="controlled-", dir=prefix))
    try:
        runtime = base / "runtime"
        (runtime / "bin").mkdir(parents=True, mode=0o700)
        interpreter = runtime / "bin" / "python3.12"
        shutil.copy2(Path(sys.executable).resolve(), interpreter)
        shutil.copytree(Path(sys.base_prefix) / "lib", runtime / "lib", symlinks=False)
        vendor = (
            runtime / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "vendor"
        )
        vendor.mkdir(mode=0o700)
        (vendor / "pickle.py").write_text("SHADOW_BOOTSTRAP_MARKER = True\n")
        source = base / "source"
        source.mkdir(mode=0o700)
        project_src = project / "src"
        for relative in (
            "researchbase/__init__.py",
            "researchbase/foundation/__init__.py",
            "researchbase/foundation/bearing_installation.py",
            "researchbase/foundation/canonical_json.py",
            "researchbase/foundation/errors.py",
            "researchbase/agent_runtime/__init__.py",
            "researchbase/agent_runtime/domain/__init__.py",
            "researchbase/agent_runtime/domain/research_task.py",
            "researchbase/agent_runtime/domain/bearing_evaluation.py",
        ):
            dest = source / relative
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(project_src / relative, dest)
        (source / "bootstrap.py").write_text(BOOTSTRAP)
        # Normalize the operator-owned copy before inventory and before exec.
        for current, dirs, files in os.walk(base):
            Path(current).chmod(0o700)
            for name in dirs:
                (Path(current) / name).chmod(0o700)
            for name in files:
                p = Path(current) / name
                p.chmod(0o700 if p == interpreter else 0o600)
        records = base / "records"
        records.mkdir(mode=0o700)
        lib = runtime / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
        measurement = subprocess.run(
            [
                str(interpreter),
                "-I",
                "-S",
                "-B",
                "-c",
                "import sys; sys.path[:]=sys.argv[1:]; import hashlib,marshal; "
                "from researchbase.agent_runtime.domain.bearing_evaluation import evaluate; "
                "print(hashlib.sha256(marshal.dumps(evaluate.__code__, "
                "marshal.version)).hexdigest())",
                str(source),
                str(lib),
                str(lib / "lib-dynload"),
            ],
            env={"TMPDIR": os.environ["TMPDIR"]},
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        u = os.uname()
        m: dict[str, Any] = dict(
            version=1,
            deployment_id="test",
            provenance="test-copy",
            namespace="test",
            artifact_sha256="0" * 64,
            callable_module="researchbase.agent_runtime.domain.bearing_evaluation",
            callable_qualname="evaluate",
            callable_code_sha256=measurement.stdout.strip(),
            runtime=dict(
                implementation=sys.implementation.name,
                cache_tag=sys.implementation.cache_tag,
                full_version=sys.version,
                marshal_version=marshal.version,
            ),
            platform=dict(
                system=u.sysname, release=u.release, version=u.version, machine=u.machine
            ),
            interpreter_path=str(interpreter),
            interpreter=_identity(interpreter),
            roots=[
                _root("source", "package", source),
                _root("runtime", "runtime", runtime / "lib"),
            ],
            limits=dict(
                max_roots=16,
                max_files=50000,
                max_total_bytes=4294967296,
                max_file_bytes=536870912,
                max_record_bytes=8388608,
                max_elapsed_seconds=120,
            ),
        )
        m["artifact_sha256"] = _artifact_digest(_parse_manifest(json.dumps(m).encode()))
        manifest = records / "manifest.json"
        manifest.write_text(json.dumps(m, separators=(",", ":")))
        manifest.chmod(0o600)
        approval = dict(
            version=1,
            deployment_id="test",
            provenance="test-copy",
            namespace="test",
            artifact_sha256=m["artifact_sha256"],
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            host=os.uname().nodename,
            uid=os.getuid(),
            expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            callable_module=m["callable_module"],
            callable_qualname="evaluate",
        )
        (records / "approval.json").write_text(json.dumps(approval, separators=(",", ":")))
        (records / "approval.json").chmod(0o600)
        print(
            "FROZEN BEFORE EXEC",
            [
                (r["label"], len(r["files"]), sum(f["identity"]["size"] for f in r["files"]))
                for r in m["roots"]
            ],
            "interpreter_bytes",
            m["interpreter"]["size"],
            "artifact",
            m["artifact_sha256"],
            "manifest_sha256",
            approval["manifest_sha256"],
            flush=True,
        )
        yield base, interpreter
    finally:
        shutil.rmtree(base)


@pytest.mark.parametrize(
    "scenario",
    [
        "positive",
        "stale",
        "preloaded-stdlib",
        "shadow-stdlib",
        "path-hook",
        "path-traversal",
        "fifo",
        "expiry",
        "final-expiry",
        "final-time",
    ],
)
def test_controlled_startup(installation, scenario):
    base, interpreter = installation
    if scenario != "positive":
        control = _child(base, interpreter, "positive")
        assert control.returncode == 0, control.stdout + control.stderr
    run = subprocess.run(
        [str(interpreter), "-I", "-S", "-B", str(base / "source/bootstrap.py"), scenario],
        env={"TMPDIR": os.environ["TMPDIR"]},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    print(run.stdout, run.stderr)
    assert run.returncode == 0
    assert ("POSITIVE hash_reads=" if scenario == "positive" else "REJECT ") in run.stdout


def test_record_hash_read_accounting_at_selected_boundaries(installation):
    base, _ = installation
    paths = [base / "records/manifest.json", base / "records/approval.json"]
    sizes = [p.stat().st_size for p in paths]
    obs = _Observation()
    for path in paths:
        obs.read(path, 8 * 1024 * 1024, record=True)
    assert (obs.files, obs.total) == (2, sum(sizes))
    limits = Limits(1, 2, sum(sizes), max(sizes), 8 * 1024 * 1024, 120)
    _bounds(obs, limits, *sizes)
    with pytest.raises(InstallationError, match="inventory limit"):
        obs.read(paths[0], 8 * 1024 * 1024, record=True)
    for too_small in (
        Limits(1, 1, sum(sizes), max(sizes), 8 * 1024 * 1024, 120),
        Limits(1, 2, sum(sizes) - 1, max(sizes), 8 * 1024 * 1024, 120),
    ):
        with pytest.raises(InstallationError, match="inventory limit"):
            _bounds(obs, too_small, *sizes)


def test_elapsed_boundary_is_not_clipped(monkeypatch):
    obs = _Observation()
    obs.start = 100.0
    obs.seconds = 120
    monkeypatch.setattr(bi.time, "monotonic", lambda: 220.0)
    obs.check_time()
    monkeypatch.setattr(bi.time, "monotonic", lambda: 220.001)
    with pytest.raises(InstallationError, match="verification timeout"):
        obs.check_time()


def _child(base, interpreter, *args):
    return subprocess.run(
        [str(interpreter), "-I", "-S", "-B", str(base / "source/bootstrap.py"), *args],
        env={"TMPDIR": os.environ["TMPDIR"]},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize(
    "diagnostic",
    [
        "file identity mismatch",
        "callable code mismatch",
        "callable binding mismatch",
        "unapproved module origin",
        "bootstrap import state changed",
    ],
)
def test_finalization_rejects_changed_observations(installation, diagnostic):
    base, interpreter = installation
    control = _child(base, interpreter, "positive")
    assert control.returncode == 0, control.stdout + control.stderr
    result = _child(base, interpreter, "final-negative", diagnostic)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REJECT final" in result.stdout


@pytest.mark.parametrize(
    "variant,diagnostic",
    [
        ("scope", "operator record scope mismatch"),
        ("host", "operator record host or uid mismatch"),
        ("expiry", "operator record expired"),
        ("platform", "platform identity mismatch"),
        ("root", "root identity mismatch"),
        ("size", "interpreter bytes"),
        ("record-mode", "unprotected operator record"),
        ("duplicate", "duplicate key version"),
        ("unknown", "approval fields"),
        ("extra", "unexpected inventory file"),
        ("missing", "missing inventory file"),
        ("symlink", "unsupported inventory entry"),
    ],
)
def test_preparation_rejects_changed_observations(installation, variant, diagnostic):
    base, interpreter = installation
    control = _child(base, interpreter, "positive")
    assert control.returncode == 0, control.stdout + control.stderr
    manifest_path = base / "records/manifest.json"
    approval_path = base / "records/approval.json"
    manifest_bytes, approval_bytes = manifest_path.read_bytes(), approval_path.read_bytes()
    m, a = json.loads(manifest_bytes), json.loads(approval_bytes)
    victim = base / "source/researchbase/foundation/errors.py"
    saved = base / "records/saved-source"
    extra = base / "source/unexpected.py"
    try:
        if variant == "scope":
            a["namespace"] = "wrong"
        elif variant == "host":
            a["host"] = "wrong"
        elif variant == "expiry":
            a["expires_at"] = "2000-01-01T00:00:00Z"
        elif variant == "platform":
            m["platform"]["machine"] = "wrong"
        elif variant == "root":
            m["roots"][0]["inode"] += 1
        elif variant == "size":
            m["limits"]["max_file_bytes"] = 1
        elif variant == "unknown":
            a["unexpected"] = True
        elif variant == "extra":
            extra.write_text("pass\n")
        elif variant in ("missing", "symlink"):
            victim.rename(saved)
            if variant == "symlink":
                victim.symlink_to(saved)
        manifest_path.write_text(json.dumps(m, separators=(",", ":")))
        a["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        approval_path.write_text(json.dumps(a, separators=(",", ":")))
        if variant == "record-mode":
            approval_path.chmod(0o644)
        if variant == "duplicate":
            approval_path.write_bytes(
                approval_path.read_bytes().replace(b'{"version":1', b'{"version":1,"version":1', 1)
            )
        result = _child(base, interpreter, "prepare-negative", diagnostic)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "REJECT prepare" in result.stdout
    finally:
        if extra.exists():
            extra.unlink()
        if variant == "symlink" and victim.is_symlink():
            victim.unlink()
        if saved.exists():
            saved.rename(victim)
        manifest_path.write_bytes(manifest_bytes)
        approval_path.write_bytes(approval_bytes)
        approval_path.chmod(0o600)
