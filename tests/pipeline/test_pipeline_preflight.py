"""Real kernel tests use only two new simulated online/root directories."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts import pipeline_preflight as t
from scripts.pipeline_safety import SafetyError

MAC = pytest.mark.skipif(
    sys.platform != "darwin", reason="real macOS Seatbelt required; no fallback"
)


def invoke(r, *args):
    v = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.pipeline_preflight", "run", "--root", str(r), *args],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
    )
    return v.returncode


def save(r, m):
    (r / "manifest.json").write_text(json.dumps(m))


def fixture(tmp_path) -> tuple[Path, Path, dict[str, Any]]:
    p = tmp_path.resolve()
    r = p / "root"
    o = p / "online"
    r.mkdir(mode=0o700)
    o.mkdir()
    (o / "empty").mkdir()
    (r / ".deny-canary").write_bytes(b"protected-canary")
    for n in ("stdout", "stderr"):
        (o / n).write_text("original")
    script = r / "scenario.py"
    script.write_text("""import json,plistlib,sys
from pathlib import Path
from typing import Any
r=Path(__file__).resolve().parent;phase=sys.argv[-1];m=json.loads((r/'manifest.json').read_text())
p=next(p for p in m['plists'] if p['role']==('old' if phase=='rollback' else 'replacement'))
v=plistlib.loads(Path(p['path']).read_bytes())
for k in ('StandardOutPath','StandardErrorPath'):Path(v[k]).write_text('fixture '+phase)
raise SystemExit(23 if phase=='rollback' else 0)
""")
    plists = []
    for role in ("old", "replacement"):
        p = r / (role + ".plist")
        v = dict(
            Label="fixture." + role,
            ProgramArguments=[
                sys.executable,
                "-B",
                "-m",
                "scripts.pipeline_wakeup",
                str(r / "payload/attempt-0" / (role + ".json")),
            ],
            StandardOutPath=str(r / "payload/attempt-0" / (role + ".stdout")),
            StandardErrorPath=str(r / "payload/attempt-0" / (role + ".stderr")),
        )
        p.write_bytes(plistlib.dumps(v))
        old = r / (role + ".original.plist")
        old.write_bytes(p.read_bytes())
        plists.append(
            dict(
                role=role,
                path=str(p),
                sha256=t.sha(p),
                original_path=str(old),
                original_sha256=t.sha(old),
                path_mapping={},
            )
        )
    b = r / "bindings.json"
    b.write_text(json.dumps(dict(config=str(r / "payload/attempt-0/old.json"))))
    base_runtime = Path(sys.base_prefix).resolve()
    runtime = Path(sys.executable).parents[2]
    m = dict(
        interpreter_inputs=[
            dict(
                role="current",
                executable=sys.executable,
                resolved_executable=str(Path(sys.executable).resolve()),
                executable_sha256=t.sha(Path(sys.executable).resolve()),
                base_runtime=str(base_runtime),
                path_aliases=sorted(
                    set(
                        t.interpreter_aliases(Path(sys.executable))
                        + t.interpreter_aliases(
                            Path(
                                (Path(sys.executable).parents[1] / "pyvenv.cfg")
                                .read_text()
                                .splitlines()[0]
                                .split("=", 1)[1]
                                .strip()
                            )
                        )
                    )
                ),
            )
        ],
        version=1,
        python=sys.executable,
        online_inputs=[str(o), str(runtime), str(base_runtime)],
        script=str(script),
        script_sha256=t.sha(script),
        bindings=[str(b)],
        plists=plists,
        timeout=10,
        deployment=None,
    )
    save(r, m)
    return r, o, m


def test_full_inventory_includes_logs_emptydirs_unreferenced_history(tmp_path):
    _, o, _ = fixture(tmp_path)
    before = t.inventory([o])
    assert before[str(o / "empty")]["kind"] == "directory"
    assert before[str(o / "stdout")]["sha256"] == hashlib.sha256(b"original").hexdigest()
    (o / "unreferenced").write_text("receipt")
    assert t.inventory([o]) != before
    (o / "unreferenced").unlink()
    (o / "stderr").write_text("changed")
    assert t.inventory([o]) != before


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo"])
def test_unsafe_inventory_rejects(tmp_path, kind):
    _, o, _ = fixture(tmp_path)
    p = o / "unsafe"
    if kind == "symlink":
        p.symlink_to(o / "stdout")
    elif kind == "hardlink":
        os.link(o / "stdout", p)
    else:
        os.mkfifo(p)
    with pytest.raises(SafetyError):
        t.inventory([o], strict=True)


@pytest.mark.parametrize("kind", ["unknown", "version", "overlap", "relative", "timeout", "python"])
def test_closed_manifest_no_first_write(tmp_path, kind):
    r, o, m = fixture(tmp_path)
    if kind == "unknown":
        m["extra"] = True
    elif kind == "version":
        m["version"] = 2
    elif kind == "overlap":
        m["online_inputs"] = [str(r)]
    elif kind == "relative":
        m["online_inputs"] = ["relative"]
    elif kind == "timeout":
        m["timeout"] = True
    else:
        m["python"] = "/usr/bin/python3"
    save(r, m)
    before = t.inventory([o])
    assert invoke(r) == 2
    assert not (r / "evidence").exists() and t.inventory([o]) == before


@pytest.mark.parametrize(
    "field", ["config", "StandardOutPath", "StandardErrorPath", "embedded", "env"]
)
def test_accident_old_live_plist_firstwrite_rejection(tmp_path, field):
    r, o, m = fixture(tmp_path)
    p = Path(m["plists"][0]["path"])
    v = plistlib.loads(p.read_bytes())
    if field == "config":
        v["ProgramArguments"][-1] = str(o / "cfg")
    elif field == "embedded":
        v["ProgramArguments"][-1] = "--config=" + str(o / "cfg")
    elif field == "env":
        v["EnvironmentVariables"] = {"TMPDIR": str(o)}
    else:
        v[field] = str(o / "stdout")
    p.write_bytes(plistlib.dumps(v))
    m["plists"][0]["sha256"] = t.sha(p)
    save(r, m)
    before = t.inventory([o])
    with patch.object(t, "child", side_effect=AssertionError("must not launch")):
        assert invoke(r) == 2
    assert t.inventory([o]) == before and not (r / "evidence").exists()


def test_binding_escape_firstwrite(tmp_path):
    r, o, _ = fixture(tmp_path)
    (r / "bindings.json").write_text(json.dumps({"rollback": "--config=" + str(o / "cfg")}))
    assert invoke(r) == 2 and not (r / "evidence").exists()


def test_explicit_mapping_verifies_both_plist_bytes(tmp_path):
    r, o, m = fixture(tmp_path)
    row = m["plists"][0]
    p = Path(row["original_path"])
    v = plistlib.loads(p.read_bytes())
    mapped = v["ProgramArguments"][-1]
    old = str(o / "cfg")
    v["ProgramArguments"][-1] = old
    p.write_bytes(plistlib.dumps(v))
    row.update(original_sha256=t.sha(p), path_mapping={old: mapped})
    save(r, m)
    assert t.plan(r)[3]["old"]["original_sha256"] != row["sha256"]
    row["path_mapping"] = {}
    save(r, m)
    with pytest.raises(SafetyError, match="correspondence"):
        t.plan(r)


def test_unavailable_no_fallback(tmp_path):
    r, o, _ = fixture(tmp_path)
    before = t.inventory([o])
    with (
        patch.object(t.sys, "platform", "linux"),
        patch.object(t.subprocess, "Popen", side_effect=AssertionError("must not launch")),
    ):
        with pytest.raises(SafetyError, match="unavailable"):
            t.bootstrap(r, None)
    assert not (r / "evidence").exists() and t.inventory([o]) == before


@MAC
def test_samebytes_normal_and_rollback_no_online_write(tmp_path):
    r, o, _ = fixture(tmp_path)
    before = t.inventory([o])
    assert invoke(r) == 0
    v = json.loads((r / "evidence/attempt-0/result.json").read_text())
    assert v["live_unchanged"] and v["status"] == "pass"
    assert [p["exit_code"] for p in v["phases"]] == [0, 23] and v["deployment"] == "NOT_EXECUTED"
    assert t.inventory([o]) == before and invoke(r) == 2


@MAC
@pytest.mark.parametrize(
    "attack",
    [
        "python",
        "shell",
        "dd",
        "nested",
        "symlink",
        "hardlink_source",
        "hardlink_target",
        "rename",
        "race",
    ],
)
def test_kernel_native_alias_and_race_deny(tmp_path, attack):
    r, o, _ = fixture(tmp_path)
    target = repr(str(o / "stdout"))
    alias = repr(str(r / "alias"))
    before = t.inventory([o])
    code = {
        "python": f'open({target},"w").write("bad")',
        "shell": f'import subprocess;raise SystemExit(subprocess.call(["/bin/sh","-c",\'printf bad > "$1"\',"sh",{target}]))',  # noqa: E501 — literal adversarial subprocess program
        "dd": f'import subprocess;raise SystemExit(subprocess.call(["/bin/dd","if=/dev/zero","of="+{target},"bs=1","count=1"]))',  # noqa: E501 — literal adversarial subprocess program
        "nested": f'import subprocess,sys;raise SystemExit(subprocess.call([sys.executable,"-B","-c",\'open(\'+repr({target})+\',"w").write("bad")\']))',  # noqa: E501 — literal adversarial subprocess program
        "symlink": f'import os;os.symlink({target},{alias});open({alias},"w").write("bad")',
        "hardlink_source": f"import os;os.link({target},{alias})",
        "hardlink_target": f'import os;open("inside","w").write("x");os.link("inside",{repr(str(o / "alias"))})',  # noqa: E501 — literal adversarial subprocess program
        "rename": f'import os;open("inside","w").write("x");os.rename("inside",{target})',
        "race": f"""import os,threading
p={alias};target={target}
def swap():
 for _ in range(200):
  try:os.unlink(p)
  except FileNotFoundError:pass
  try:os.symlink(target,p)
  except FileExistsError:pass
t=threading.Thread(target=swap);t.start()
for _ in range(200):
 try:
  with open(p,'w') as f:f.write('bad')
 except (PermissionError,FileNotFoundError):pass
t.join();raise SystemExit(7)
""",
    }[attack]
    observed = t.child(r, [sys.executable, "-B", "-c", code], 10)
    assert observed["exit_code"] != 0 and not observed["timed_out"] and t.inventory([o]) == before
    if attack != "race":
        assert (
            "Operation not permitted" in observed["stderr"]
            or "PermissionError" in observed["stderr"]
        )


@MAC
def test_natural_external_change_is_fail_not_filtered(tmp_path):
    r, o, _ = fixture(tmp_path)
    original = t.child

    def concurrent(*args):
        v = original(*args)
        if args[0] == r / "payload/attempt-0":
            (o / "stderr").write_text("independent timer")
        return v

    with patch.object(t, "child", side_effect=concurrent):
        assert t.run(r) == 2
    assert json.loads((r / "evidence/attempt-0/result.json").read_text())["live_unchanged"] is False


@MAC
def test_no_inherited_live_write_fd(tmp_path):
    r, o, _ = fixture(tmp_path)
    before = t.inventory([o])
    fd = os.open(o / "stdout", os.O_WRONLY)
    os.set_inheritable(fd, True)
    try:
        v = t.child(r, [sys.executable, "-B", "-c", f'import os;os.write({fd},b"bad")'], 10)
    finally:
        os.close(fd)
    assert v["exit_code"] != 0 and t.inventory([o]) == before


def test_profile_denies_write_network_and_mach(tmp_path):
    r, _, _ = fixture(tmp_path)
    p = t.profile(r)
    assert all(s in p for s in ("(deny file-write*)", "(deny network*)", "(deny mach-lookup)"))
    assert p.count("(allow file-write*") == 1 and json.dumps(str(r)) in p


def test_real_cli_unknown_and_import_no_process(tmp_path):
    cwd = Path(__file__).resolve().parents[2]
    for argv in (["unknown"], ["run", "--root", str(tmp_path), "--external-write", "/somewhere"]):
        assert (
            subprocess.run(
                [sys.executable, "-B", "-m", "scripts.pipeline_preflight", *argv],
                cwd=cwd,
                capture_output=True,
            ).returncode
            != 0
        )
    script = 'from unittest.mock import patch\nwith patch("subprocess.Popen",side_effect=AssertionError("import launched")):\n import scripts.pipeline_preflight\n'  # noqa: E501 — literal adversarial subprocess program
    assert (
        subprocess.run(
            [sys.executable, "-B", "-c", script], cwd=cwd, capture_output=True
        ).returncode
        == 0
    )
    assert list(tmp_path.iterdir()) == []


def test_readonly_symlinks_and_hardlinks_are_recorded_not_followed(tmp_path):
    r, o, _ = fixture(tmp_path)
    link = o / "python"
    link.symlink_to("/outside/readonly/python")
    os.link(o / "stdout", o / "stdout-alias")
    v = t.inventory([o])
    assert (
        v[str(link)]["kind"] == "symlink" and v[str(link)]["target"] == "/outside/readonly/python"
    )
    assert v[str(o / "stdout")]["nlink"] == 2 and str(o / "stdout-alias") in v
    with pytest.raises(SafetyError):
        t.inventory([o], strict=True)


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_preplaced_root_alias_rejects_before_payload(tmp_path, kind):
    r, o, _ = fixture(tmp_path)
    if kind == "symlink":
        (r / "alias").symlink_to(o / "stdout")
    else:
        os.link(o / "stdout", r / "alias")
    assert invoke(r) == 2 and not (r / "payload").exists()


def test_correction_budget_three_and_online_change_hardstop(tmp_path):
    r, _, _ = fixture(tmp_path)
    e = r / "evidence"
    e.mkdir()
    for i in range(4):
        a = e / f"attempt-{i}"
        a.mkdir()
        p = a / "result.json"
        p.write_text(
            json.dumps(dict(status="blocked", possible_online_write=False, quarantined=False))
        )
        if i < 3:
            assert t.next_attempt(r, t.sha(p)) == i + 1
        else:
            with pytest.raises(SafetyError, match="exhausted"):
                t.next_attempt(r, t.sha(p))
    for a in e.iterdir():
        if a.name != "attempt-0":
            (a / "result.json").unlink()
            a.rmdir()
    p = e / "attempt-0/result.json"
    p.write_text(json.dumps(dict(status="blocked", possible_online_write=True, quarantined=False)))
    with pytest.raises(SafetyError, match="cannot be retried"):
        t.next_attempt(r, t.sha(p))


def test_uncertain_or_wrong_prior_result_denies_retry(tmp_path):
    r, _, _ = fixture(tmp_path)
    a = r / "evidence/attempt-0"
    a.mkdir(parents=True)
    with pytest.raises(SafetyError, match="uncertain"):
        t.next_attempt(r, "a" * 64)
    p = a / "result.json"
    p.write_text(json.dumps(dict(status="blocked", possible_online_write=False, quarantined=False)))
    for correction in (None, "a" * 64):
        with pytest.raises(SafetyError):
            t.next_attempt(r, correction)


@MAC
def test_root_evidence_tamper_detected_without_claiming_malicious_root_sandbox(tmp_path):
    r, o, m = fixture(tmp_path)
    p = Path(m["script"])
    p.write_text(
        'from pathlib import Path\np=Path(__file__).parent/"evidence/attempt-0/intent.json"\np.write_text("tampered")\n'  # noqa: E501 — literal adversarial subprocess program
    )
    m["script_sha256"] = t.sha(p)
    save(r, m)
    before = t.inventory([o])
    assert invoke(r) == 2
    result = json.loads((r / "evidence/attempt-0/result.json").read_text())
    assert (
        result["status"] == "blocked"
        and "protected attempt" in result["failure"]
        and t.inventory([o]) == before
    )


def test_regular_inherited_stdio_refuses_before_write(tmp_path):
    r, o, _ = fixture(tmp_path)
    p = o / "stdout"
    before = p.read_bytes()
    with p.open("ab") as stream:
        v = subprocess.run(
            [sys.executable, "-B", "-m", "scripts.pipeline_preflight", "run", "--root", str(r)],
            stdout=stream,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).resolve().parents[2],
        )
    assert v.returncode == 2 and p.read_bytes() == before and not (r / "payload").exists()


@MAC
def test_unconfined_internal_entry_cannot_bypass_outer(tmp_path):
    r, _, _ = fixture(tmp_path)
    v = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.pipeline_preflight", "_outer", "--root", str(r)],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert v.returncode == 2 and not (r / "payload").exists()


@pytest.mark.parametrize("field", ["closure", "digest", "resolved", "roles"])
def test_interpreter_closure_required_before_write(tmp_path, field):
    r, _, m = fixture(tmp_path)
    if field == "closure":
        m["online_inputs"].remove(m["interpreter_inputs"][0]["base_runtime"])
    elif field == "digest":
        m["interpreter_inputs"][0]["executable_sha256"] = "0" * 64
    elif field == "resolved":
        m["interpreter_inputs"][0]["resolved_executable"] = m["script"]
    else:
        m["interpreter_inputs"] = []
    save(r, m)
    assert invoke(r) == 2 and not (r / "payload").exists()


def test_prior_resolved_binary_and_base_library_changes_observed(tmp_path):
    r, o, m = fixture(tmp_path)
    project = o / "prior-project"
    venv = project / ".venv"
    (venv / "bin").mkdir(parents=True)
    base = o / "prior-base"
    (base / "bin").mkdir(parents=True)
    (base / "lib").mkdir()
    binary = base / "bin/python3"
    binary.write_bytes(b"fixture executable bytes")
    lib = base / "lib/stdlib.py"
    lib.write_text("fixture base runtime")
    (venv / "bin/python3").symlink_to(binary)
    (venv / "pyvenv.cfg").write_text("home = " + str(base / "bin") + "\n")
    rows = [
        m["interpreter_inputs"][0],
        dict(
            role="prior",
            executable=str(venv / "bin/python3"),
            resolved_executable=str(binary),
            executable_sha256=t.sha(binary),
            base_runtime=str(base),
            path_aliases=t.interpreter_aliases(venv / "bin/python3"),
        ),
    ]
    paths = [Path(p) for p in m["online_inputs"]]
    t.interpreter_closure(rows, paths, Path(sys.executable), project)
    before = t.inventory([base])
    binary.write_bytes(b"replaced binary")
    with pytest.raises(SafetyError, match="digest drift"):
        t.interpreter_closure(rows, paths, Path(sys.executable), project)
    assert t.inventory([base]) != before
    binary.write_bytes(b"fixture executable bytes")
    before = t.inventory([base])
    lib.write_text("changed library")
    assert t.inventory([base]) != before


@MAC
def test_intent_records_actual_single_root_profile_not_workdir(tmp_path):
    r, _, _ = fixture(tmp_path)
    assert invoke(r) == 0
    intent = json.loads((r / "evidence/attempt-0/intent.json").read_text())
    assert intent["effective_write_root"] == str(r) and intent["profile"] == t.profile(r)
    assert intent["payload_workdir"] == str(r / "payload/attempt-0")
    assert "writable_root" not in intent


def test_interpreter_alias_loop_is_bounded_and_alias_metadata_snapshotted(tmp_path):
    r, o, _ = fixture(tmp_path)
    a = o / "alias-a"
    b = o / "alias-b"
    a.symlink_to(b)
    b.symlink_to(a)
    with pytest.raises(SafetyError, match="alias bound"):
        t.interpreter_aliases(a)
    b.unlink()
    b.symlink_to(o / "stdout")
    before = t.inventory([a])
    a.unlink()
    a.symlink_to(o / "stderr")
    assert t.inventory([a]) != before


def test_declared_interpreter_aliases_cannot_be_silently_omitted(tmp_path):
    r, _, m = fixture(tmp_path)
    m["interpreter_inputs"][0]["path_aliases"] = []
    save(r, m)
    assert invoke(r) == 2 and not (r / "payload").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"st_mode": 0o100666},
        {"st_mode": 0o120777},
        {"st_uid": 1},
        {"st_gid": 1},
        {"st_nlink": 2},
        {"st_rdev": os.makedev(3, 3)},
    ],
)
def test_null_identity_rejects_regular_symlink_owner_links_or_wrong_device(change):
    import types

    real = Path.lstat
    expected = dict(st_mode=0o020666, st_uid=0, st_gid=0, st_nlink=1, st_rdev=os.makedev(3, 2))

    def metadata(path, *args, **kwargs):
        if path == Path("/dev/null"):
            return types.SimpleNamespace(**{**expected, **change})
        return real(path, *args, **kwargs)

    with patch.object(Path, "lstat", metadata), pytest.raises(SafetyError, match="device identity"):
        t.null_identity()


@MAC
def test_null_identity_open_race_fails_closed():
    import types

    original = os.fstat

    def changed(fd):
        info = original(fd)
        return types.SimpleNamespace(
            **{
                key: getattr(info, key) + (1 if key == "st_ino" else 0)
                for key in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_uid",
                    "st_gid",
                    "st_nlink",
                    "st_rdev",
                )
            }
        )

    with patch.object(os, "fstat", changed), pytest.raises(SafetyError, match="changed during"):
        t.null_identity()


@MAC
def test_kernel_null_data_only_and_no_other_device_privileges(tmp_path):
    r, o, _ = fixture(tmp_path)
    before = t.inventory([o])
    identity = t.null_identity()
    program = """import ctypes,json,os
f=os.open('/dev/null',os.O_WRONLY);assert os.write(f,b'approved sink')==13;os.close(f)
check=ctypes.CDLL('/usr/lib/system/libsystem_sandbox.dylib').sandbox_check
check.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int];check.restype=ctypes.c_int
ops=['file-write-data','file-write-create','file-write-unlink','file-write-mode']
print(json.dumps({op:check(os.getpid(),op.encode(),1,ctypes.c_char_p(b'/dev/null')) for op in ops}))
"""
    observed = t.child(r, [sys.executable, "-B", "-c", program], 10)
    assert observed["exit_code"] == 0
    result = json.loads(observed["stdout"])
    assert result == {
        "file-write-data": 0,
        "file-write-create": 1,
        "file-write-unlink": 1,
        "file-write-mode": 1,
    }
    assert t.null_identity() == identity and t.inventory([o]) == before


def unit_verification_proof(tmp_path) -> Any:
    """Fabricated host receipts for parser negatives, never native acceptance."""
    import stat

    from tests.pipeline.test_pipeline_preflight_deploy import deployment_fixture

    r, o, m = deployment_fixture(tmp_path)
    data = {}
    aliases = {name for spec in m["interpreter_inputs"] for name in spec["path_aliases"]}
    binaries = {spec["resolved_executable"]: spec for spec in m["interpreter_inputs"]}
    roots = [Path(v) for v in m["online_inputs"]] + [Path(v) for v in aliases]
    tops = [p for p in roots if not any(other != p and p.is_relative_to(other) for other in roots)]
    names = set(roots) | {Path(v) for v in binaries}
    for p in list(names):
        current = p.parent
        while current not in tops and any(current.is_relative_to(top) for top in tops):
            names.add(current)
            current = current.parent
    for index, p in enumerate(sorted(names)):
        row = dict(
            dev=1,
            ino=index + 1,
            mode=stat.S_IFDIR | 0o700,
            uid=os.getuid(),
            gid=0,
            nlink=1,
            size=0,
            mtime_ns=0,
            ctime_ns=0,
            kind="directory",
            children=[],
        )
        if str(p) in aliases:
            target = os.readlink(p)
            row.update(
                mode=stat.S_IFLNK | 0o777,
                kind="symlink",
                target=target,
                target_sha256=hashlib.sha256(os.fsencode(target)).hexdigest(),
            )
            row.pop("children")
        elif str(p) in binaries:
            row.update(
                mode=stat.S_IFREG | 0o600,
                kind="file",
                size=p.stat().st_size,
                sha256=binaries[str(p)]["executable_sha256"],
            )
            row.pop("children")
        data[str(p)] = row
    for name, _row in data.items():
        parent = data.get(str(Path(name).parent))
        if parent is not None:
            parent["children"].append(Path(name).name)
    for row in data.values():
        if "children" in row:
            row["children"].sort()
    protected = {
        "manifest.json": (r / "manifest.json").read_bytes().hex(),
        "script": Path(m["script"]).read_bytes().hex(),
    }
    for name in m["bindings"] + [v[k] for v in m["plists"] for k in ("path", "original_path")]:
        protected[name] = Path(name).read_bytes().hex()
    device = dict(
        dev=1, ino=2, mode=stat.S_IFCHR | 0o666, uid=0, gid=0, nlink=1, rdev=os.makedev(3, 2)
    )
    intent = dict(
        attempt=0,
        inputs=protected,
        before=data,
        null_device=device,
        effective_write_root=str(r),
        payload_workdir=str(r / "payload/attempt-0"),
        profile=t.profile(r),
    )

    def put(relative, value):
        p = r / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, sort_keys=True) + "\n")
        return t.sha(p)

    intent_sha = put("evidence/attempt-0/intent.json", intent)
    proofs = []
    phases = []
    stages = {}
    for phase, exit_code in (("normal", 0), ("rollback", 23)):
        relative = f"payload/attempt-0/{phase}/adapter-result.json"
        plist = str(r / "payload/attempt-0/fixture" / m["deployment"]["prior_plist"])
        stage = dict(
            success=True,
            phase=phase,
            payload_sha256=m["script_sha256"],
            same_payload_bytes=True,
            baseline=m["deployment"]["head"],
            required_feature54=m["deployment"]["required_feature54"],
            launchctl="SIMULATED_ONLY",
            clock="SIMULATED_ONLY",
            calls=[["launchctl", a, f"gui/{os.getuid()}", plist] for a in ("bootstrap", "bootout")],
            mapping=[],
            baseline_git=[
                dict(
                    argv=["git", "-C", m["deployment"]["runtime"], "rev-parse", "HEAD"],
                    exit_code=0,
                    stdout=m["deployment"]["head"] + "\n",
                    stderr="",
                ),
                dict(
                    argv=[
                        "git",
                        "-C",
                        m["deployment"]["runtime"],
                        "merge-base",
                        "--is-ancestor",
                        m["deployment"]["required_feature54"],
                        m["deployment"]["head"],
                    ],
                    exit_code=0,
                    stdout="",
                    stderr="",
                ),
            ],
        )
        stages[phase] = stage
        proofs.append(dict(phase=phase, path=relative, sha256=put(relative, stage)))
        phases.append(
            dict(
                phase=phase,
                exit_code=exit_code,
                timed_out=False,
                descendants_stopped=True,
                stdout="",
                stderr="",
            )
        )
    result = dict(
        version=1,
        status="pass",
        attempt=0,
        null_device=device,
        possible_online_write=False,
        quarantined=False,
        live_unchanged=True,
        failure=None,
        before=data,
        after=data,
        phases=phases,
        intent_sha256=intent_sha,
        stage_proofs=proofs,
        plist_hashes={
            v["role"]: dict(
                mapped_sha256=v["sha256"],
                original_sha256=v["original_sha256"],
                path_mapping=v["path_mapping"],
            )
            for v in m["plists"]
        },
        mode="isolated_rehearsal",
        deployment="NOT_EXECUTED",
        adapter="deployment",
        correction_budget="maximum3 explicit corrections; no automatic retry",
    )
    result_sha = put("evidence/attempt-0/result.json", result)
    context = t.VerificationContext(
        root=str(r),
        attempt=0,
        result_sha256=result_sha,
        manifest_sha256=t.sha(r / "manifest.json"),
        payload_sha256=m["script_sha256"],
        release_head=m["deployment"]["head"],
        python=sys.executable,
        expected_bindings=(("bindings.json", t.sha(r / "bindings.json")),),
    )
    return r, m, intent, result, stages, context, put


def test_readonly_verifier_validates_unit_receipts_without_commands_or_online_reads(tmp_path):
    r, m, _, _, _, ctx, _ = unit_verification_proof(tmp_path)
    before = t.inventory([r])
    original = t.read_artifact
    reads = []

    def only_root(root, relative):
        assert root == str(r)
        reads.append(relative)
        return original(root, relative)

    with (
        patch.object(t.subprocess, "Popen", side_effect=AssertionError("verification launched")),
        patch.object(t, "inventory", side_effect=AssertionError("online rescan")),
        patch.object(t, "read_artifact", side_effect=only_root),
    ):
        verified = t.verify_result(ctx)
    assert verified["status"] == "verified" and verified["current_online_state"] == "NOT_RESCANNED"
    assert t.inventory([r]) == before and "payload/attempt-0/rollback/adapter-result.json" in reads
    assert verified["manifest_sha256"] == ctx.manifest_sha256


@pytest.mark.parametrize(
    "field",
    [
        "result_sha256",
        "manifest_sha256",
        "payload_sha256",
        "release_head",
        "python",
        "attempt",
        "root",
    ],
)
def test_nullable_verification_context_never_touches_files(field):
    value: dict[str, Any] = dict(
        root="/not-a-root",
        attempt=0,
        result_sha256="a" * 64,
        manifest_sha256="b" * 64,
        payload_sha256="c" * 64,
        release_head="d" * 40,
        python=sys.executable,
    )
    value[field] = None
    with (
        patch.object(t, "read_artifact", side_effect=AssertionError("premature Root read")),
        pytest.raises((SafetyError, TypeError)),
    ):
        t.verify_result(t.VerificationContext(**value))


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "unknown",
        "online_change",
        "failed",
        "quarantined",
        "phase_missing",
        "phase_unknown",
        "phase_bool_exit",
        "intent",
        "snapshot_missing",
        "snapshot_unknown",
        "stage_sha",
        "stage_payload",
        "stage_head",
        "native_git",
        "service_trace",
        "manifest_head",
        "manifest_interpreter",
    ],
)
def test_result_verifier_rejects_semantic_tampering_even_with_new_result_digest(tmp_path, mutation):
    from dataclasses import replace

    r, m, intent, result, stages, ctx, put = unit_verification_proof(tmp_path)
    if mutation == "status":
        result["status"] = "blocked"
    elif mutation == "unknown":
        result["extra"] = True
    elif mutation == "online_change":
        result["possible_online_write"] = True
    elif mutation == "failed":
        result["failure"] = "observed error"
    elif mutation == "quarantined":
        result["quarantined"] = True
    elif mutation == "phase_missing":
        result["phases"].pop()
    elif mutation == "phase_unknown":
        result["phases"][0]["extra"] = "unsupported"
    elif mutation == "phase_bool_exit":
        result["phases"][0]["exit_code"] = False
    elif mutation == "intent":
        intent["effective_write_root"] = str(r.parent)
        result["intent_sha256"] = put("evidence/attempt-0/intent.json", intent)
    elif mutation == "snapshot_missing":
        key = next(k for k, v in result["before"].items() if v["kind"] == "file")
        result["before"].pop(key)
    elif mutation == "snapshot_unknown":
        next(iter(result["before"].values()))["extra"] = 0
    elif mutation == "stage_sha":
        result["stage_proofs"][0]["sha256"] = "0" * 64
    elif mutation in ("stage_payload", "stage_head", "native_git", "service_trace"):
        stage = stages["normal"]
        if mutation == "stage_payload":
            stage["payload_sha256"] = "0" * 64
        elif mutation == "stage_head":
            stage["baseline"] = "0" * 40
        elif mutation == "native_git":
            stage["baseline_git"][0]["exit_code"] = 1
        else:
            stage["calls"] = []
        result["stage_proofs"][0]["sha256"] = put(result["stage_proofs"][0]["path"], stage)
    else:
        if mutation == "manifest_head":
            m["deployment"]["head"] = "0" * 40
        else:
            m["python"] = "/wrong/.venv/bin/python3"
        ctx = replace(ctx, manifest_sha256=put("manifest.json", m))
    ctx = replace(ctx, result_sha256=put("evidence/attempt-0/result.json", result))
    with pytest.raises((SafetyError, OSError, ValueError, KeyError, TypeError)):
        t.verify_result(ctx)


@pytest.mark.parametrize(
    "mutation",
    [
        "tampered_result",
        "missing_result",
        "wrong_expected_hash",
        "wrong_expected_payload",
        "wrong_expected_head",
        "wrong_expected_python",
        "binding_pin",
        "symlink",
        "hardlink",
    ],
)
def test_result_verifier_rejects_pins_missing_and_aliases(tmp_path, mutation):
    from dataclasses import replace

    r, _, _, _, _, ctx, _ = unit_verification_proof(tmp_path)
    p = r / "evidence/attempt-0/result.json"
    if mutation == "tampered_result":
        p.write_text("{}")
    elif mutation == "missing_result":
        p.unlink()
    elif mutation == "wrong_expected_hash":
        ctx = replace(ctx, manifest_sha256="0" * 64)
    elif mutation == "wrong_expected_payload":
        ctx = replace(ctx, payload_sha256="0" * 64)
    elif mutation == "wrong_expected_head":
        ctx = replace(ctx, release_head="0" * 40)
    elif mutation == "wrong_expected_python":
        ctx = replace(ctx, python="/wrong/.venv/bin/python3")
    elif mutation == "binding_pin":
        ctx = replace(ctx, expected_bindings=(("bindings.json", "0" * 64),))
    elif mutation == "symlink":
        target = r / "saved-result"
        p.rename(target)
        p.symlink_to(target)
    else:
        os.link(p, r / "alias-result")
    with pytest.raises((SafetyError, OSError, ValueError)):
        t.verify_result(ctx)


def test_verify_cli_readonly_and_unknown_flags(tmp_path):
    r, _, _, _, _, ctx, _ = unit_verification_proof(tmp_path)
    args = [
        sys.executable,
        "-B",
        "-m",
        "scripts.pipeline_preflight",
        "verify",
        "--root",
        ctx.root,
        "--attempt",
        "0",
        "--result-sha256",
        ctx.result_sha256,
        "--manifest-sha256",
        ctx.manifest_sha256,
        "--payload-sha256",
        ctx.payload_sha256,
        "--release-head",
        ctx.release_head,
        "--python",
        ctx.python,
        "--binding",
        "bindings.json=" + ctx.expected_bindings[0][1],
    ]
    before = t.inventory([r])
    v = subprocess.run(
        args, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2]
    )
    assert v.returncode == 0, v.stderr + v.stdout
    assert json.loads(v.stdout)["status"] == "verified" and t.inventory([r]) == before
    assert (
        subprocess.run(
            args + ["--unknown"], capture_output=True, cwd=Path(__file__).resolve().parents[2]
        ).returncode
        != 0
    )
