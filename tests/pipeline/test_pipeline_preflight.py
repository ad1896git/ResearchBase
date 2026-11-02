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
    m = dict(
        version=1,
        python=sys.executable,
        online_inputs=[str(o)],
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
    with patch.object(t.sys, "platform", "linux"):
        assert t.run(r) == 2
    result = json.loads((r / "evidence/attempt-0/result.json").read_text())
    assert result["status"] == "blocked" and result["phases"] == []
    assert t.inventory([o]) == before


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
        p.write_text(json.dumps(dict(status="blocked", possible_online_write=False)))
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
    p.write_text(json.dumps(dict(status="blocked", possible_online_write=True)))
    with pytest.raises(SafetyError, match="cannot be retried"):
        t.next_attempt(r, t.sha(p))


def test_uncertain_or_wrong_prior_result_denies_retry(tmp_path):
    r, _, _ = fixture(tmp_path)
    a = r / "evidence/attempt-0"
    a.mkdir(parents=True)
    with pytest.raises(SafetyError, match="uncertain"):
        t.next_attempt(r, "a" * 64)
    p = a / "result.json"
    p.write_text(json.dumps(dict(status="blocked", possible_online_write=False)))
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
