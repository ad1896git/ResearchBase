"""Real temporary installation; no registration or deployment authority."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BOOTSTRAP = r"""import sys
from pathlib import Path

base = Path(__file__).parent.parent
src = base / "source"
lib = base / "runtime" / "lib" / "python3.12"
sys.path[:] = [str(src), str(lib), str(lib / "lib-dynload")]
import hashlib, json, marshal, os, pickle, socket, stat, time
from datetime import UTC, datetime, timedelta
from researchbase.foundation import bearing_installation as bi
from researchbase.agent_runtime.domain.bearing_evaluation import evaluate

records = base / "records"
manifest_path = records / "manifest.json"
approval_path = records / "approval.json"


def ident(path):
    s = path.stat()
    return dict(
        device=s.st_dev,
        inode=s.st_ino,
        size=s.st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        owner_uid=s.st_uid,
        mode=stat.S_IMODE(s.st_mode),
    )


def root(label, kind, path):
    s = path.stat()
    files = []
    for current, dirs, names in os.walk(path):
        for name in sorted(names):
            p = Path(current) / name
            rel = p.relative_to(path).as_posix()
            kind_file = (
                "source"
                if p.suffix == ".py"
                else "bytecode"
                if p.suffix == ".pyc"
                else "native"
                if p.suffix in (".so", ".dylib")
                else "runtime"
            )
            files.append(dict(relative_path=rel, kind=kind_file, identity=ident(p)))
    return dict(
        label=label,
        kind=kind,
        path=str(path),
        device=s.st_dev,
        inode=s.st_ino,
        owner_uid=s.st_uid,
        mode=stat.S_IMODE(s.st_mode),
        files=files,
    )


def dump(path, obj):
    path.write_bytes(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode())
    path.chmod(0o600)


u = os.uname()
interpreter = Path(os.path.realpath(sys.executable))
m = dict(
    version=1,
    deployment_id="temporary-test",
    provenance="test-source-copy",
    namespace="unit-test",
    artifact_sha256="0" * 64,
    callable_module=evaluate.__module__,
    callable_qualname=evaluate.__qualname__,
    callable_code_sha256=hashlib.sha256(
        marshal.dumps(evaluate.__code__, marshal.version)
    ).hexdigest(),
    runtime=dict(
        implementation=sys.implementation.name,
        cache_tag=sys.implementation.cache_tag,
        full_version=sys.version,
        marshal_version=marshal.version,
    ),
    platform=dict(system=u.sysname, release=u.release, version=u.version, machine=u.machine),
    interpreter_path=str(interpreter),
    interpreter=ident(interpreter),
    roots=[root("source", "package", src), root("runtime", "runtime", base / "runtime" / "lib")],
    limits=dict(
        max_roots=16,
        max_files=50000,
        max_total_bytes=4294967296,
        max_file_bytes=536870912,
        max_record_bytes=8388608,
        max_elapsed_seconds=120,
    ),
)
m["artifact_sha256"] = bi._artifact_digest(bi._parse_manifest(json.dumps(m).encode()))
a = dict(
    version=1,
    deployment_id=m["deployment_id"],
    provenance=m["provenance"],
    namespace=m["namespace"],
    artifact_sha256=m["artifact_sha256"],
    manifest_sha256="",
    host=socket.gethostname(),
    uid=os.getuid(),
    expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    callable_module=m["callable_module"],
    callable_qualname=m["callable_qualname"],
)


def records_write():
    dump(manifest_path, m)
    a["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    dump(approval_path, a)


def verify():
    return bi.verify_installation(
        approval_path=approval_path,
        manifest_path=manifest_path,
        namespace="unit-test",
        fixed_callable=evaluate,
    )


def rejected(label, diagnostic):
    try:
        verify()
    except bi.InstallationError as exc:
        assert diagnostic in str(exc), (label, str(exc))
        print("REJECT", label, str(exc), flush=True)
    else:
        raise AssertionError("accepted " + label)


records_write()
proof = verify()
print("POSITIVE files=%d bytes=%d seconds=%.6f" % proof.measurements, flush=True)
try:
    bi.VerifiedInstallation()
except TypeError:
    pass
else:
    raise AssertionError("public constructor")
try:
    pickle.dumps(proof)
except TypeError:
    pass
else:
    raise AssertionError("serialized evidence")

# Each case changes one observation, restores it, and verifies the same real setup.
a["namespace"] = "wrong"
records_write()
rejected("scope", "scope mismatch")
a["namespace"] = m["namespace"]
records_write()
verify()
a["expires_at"] = "2000-01-01T00:00:00Z"
records_write()
rejected("expiry", "expiry mismatch")
a["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
records_write()
verify()
extra = src / "unexpected.py"
extra.write_text("pass\n")
rejected("extra file", "unexpected inventory file")
extra.unlink()
verify()
original_code = evaluate.__code__
evaluate.__code__ = (lambda: None).__code__
rejected("code", "callable code mismatch")
evaluate.__code__ = original_code
verify()
m["platform"]["machine"] = "wrong"
records_write()
rejected("platform", "platform identity mismatch")
m["platform"]["machine"] = u.machine
records_write()
verify()
victim = src / "researchbase" / "foundation" / "errors.py"
saved = records / "saved-source"
victim.rename(saved)
rejected("missing file", "missing inventory file")
saved.rename(victim)
verify()
original = victim.read_bytes()
victim.write_bytes(original + b"\n")
rejected("modified file", "file identity mismatch")
victim.write_bytes(original)
verify()
victim.rename(saved)
victim.symlink_to(saved)
rejected("symlink", "unsupported inventory entry")
victim.unlink()
saved.rename(victim)
verify()
sys.path.append(str(records))
rejected("import path", "unapproved import path")
sys.path.pop()
verify()
sys.path.append(str(src) + "/../records")
rejected("import traversal", "invalid import path")
sys.path.pop()
verify()
approval_path.write_bytes(
    approval_path.read_bytes().replace(b'{"version":1', b'{"version":1,"version":1', 1)
)
rejected("duplicate approval", "duplicate key version")
records_write()
verify()
a["host"] = "wrong-host"
records_write()
rejected("host", "host, uid or expiry mismatch")
a["host"] = socket.gethostname()
records_write()
verify()
m["limits"]["max_file_bytes"] = 1
records_write()
rejected("file bound", "interpreter bytes")
m["limits"]["max_file_bytes"] = 536870912
records_write()
verify()
m["roots"][0]["inode"] += 1
records_write()
rejected("root identity", "root identity mismatch")
m["roots"][0]["inode"] -= 1
records_write()
verify()
approval_path.chmod(0o644)
rejected("record mode", "unprotected operator record")
approval_path.chmod(0o600)
verify()
module = sys.modules[evaluate.__module__]
saved_origin = module.__file__
module.__file__ = str(records / "unapproved.py")
rejected("module origin", "unapproved module origin")
module.__file__ = saved_origin
verify()
sys.meta_path.append(object())
rejected("import hook", "unsupported import hooks")
sys.meta_path.pop()
verify()
a["unexpected"] = 1
records_write()
rejected("unknown approval field", "approval fields")
del a["unexpected"]
records_write()
verify()
old_evaluate = module.evaluate
module.evaluate = lambda: None
rejected("callable binding", "callable binding mismatch")
module.evaluate = old_evaluate
verify()
print("ALL CASES COMPLETE", flush=True)
"""


def test_real_isolated_installation(tmp_path: Path) -> None:
    base = tmp_path / "installation"
    base.mkdir(mode=0o700)
    runtime = base / "runtime"
    runtime.mkdir(mode=0o700)
    (runtime / "bin").mkdir(mode=0o700)
    interpreter = runtime / "bin" / "python3.12"
    shutil.copy2(Path(sys.executable).resolve(), interpreter)
    # Materialize the selected runtime's setup aliases as regular file copies.
    shutil.copytree(Path(sys.base_prefix) / "lib", runtime / "lib", symlinks=False)
    source = base / "source"
    source.mkdir(mode=0o700)
    project_src = Path(__file__).resolve().parents[3] / "src"
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
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(project_src / relative, destination)
    bootstrap = source / "bootstrap.py"
    bootstrap.write_text(BOOTSTRAP)
    (base / "records").mkdir(mode=0o700)
    env = {"TMPDIR": os.environ["TMPDIR"]}
    result = subprocess.run(
        [str(interpreter), "-I", "-S", "-B", str(bootstrap)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0
    assert "POSITIVE files=" in result.stdout
    assert "ALL CASES COMPLETE" in result.stdout
