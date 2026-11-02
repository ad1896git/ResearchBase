"""Fixed, confined deploy rehearsal adapter. No real launchd/remote/model calls."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import plistlib
import runpy
import shutil
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch

# Invoked by absolute path in a separately confined process; never imported payload in parent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.pipeline_preflight import (  # noqa: E402
    beneath,
    canonical,
    checked_plist,
    exact,
    inventory,
    require,
    sha,
)

LEGACY = ("com.researchbase.autopilot", "com.researchbase.watchdog")
FILES = (
    ".pipeline/state.json",
    ".pipeline/queue.json",
    ".pipeline/bin/autopilot.py",
    ".pipeline/bin/run_forever.sh",
    ".pipeline/bin/watchdog.sh",
)


def validate_deployment(value, root, writable, inputs, python):
    exact(
        value,
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
    require(type(value["version"]) is int and value["version"] == 1, "deployment adapter schema")
    require(
        value["required_feature54"] == "7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2",
        "required54 identity",
    )
    require(
        type(value["head"]) is str
        and len(value["head"]) == 40
        and all(c in "0123456789abcdef" for c in value["head"]),
        "deployment exact head",
    )
    require(value["runtime"] == str(python.parents[2]), "deployment fixed runtime")
    require(
        any(
            Path(value["runtime"]) == p or Path(value["runtime"]).is_relative_to(p) for p in inputs
        ),
        "undeclared target runtime",
    )
    require(type(value["stamp"]) is str and value["stamp"].isalnum(), "deployment stamp")
    prior_runtime = canonical(value["prior_runtime"])
    require(
        any(prior_runtime == p or prior_runtime.is_relative_to(p) for p in inputs),
        "undeclared prior runtime",
    )
    require(type(value["path_aliases"]) is dict, "explicit path aliases")
    for old, new in value["path_aliases"].items():
        canonical(old)
        relative(new, writable / "fixture")
    require(type(value["mappings"]) is list and value["mappings"], "deployment mappings")
    destinations = []
    for row in value["mappings"]:
        exact(row, ("source", "destination"))
        source = canonical(row["source"])
        require(
            any(source == p or source.is_relative_to(p) for p in inputs),
            "undeclared readonly source",
        )
        target = relative(row["destination"], writable / "fixture")
        require(
            not any(
                target == old or target.is_relative_to(old) or old.is_relative_to(target)
                for old in destinations
            ),
            "overlapping materialization",
        )
        destinations.append(target)
    require(type(value["rewrite_json"]) is list, "rewrite list")
    for path in value["rewrite_json"]:
        relative(path, writable / "fixture")
    relative(value["prior_plist"], writable / "fixture")
    require(
        type(value["executable_dirs"]) is list and value["executable_dirs"],
        "executable directories",
    )
    for path in value["executable_dirs"]:
        canonical(path)
    require(type(value["codex_version"]) is str and value["codex_version"], "codex version pin")
    return value["executable_dirs"]


def relative(text, base):
    require(
        type(text) is str
        and text
        and not text.startswith("/")
        and all(p not in ("", ".", "..") for p in text.split("/")),
        "relative fixture path",
    )
    return beneath(str(base / text), base)


def materialize(model, writable):
    fixture = writable / "fixture"
    fixture.mkdir(mode=0o700)
    mappings = [
        (canonical(v["source"]), relative(v["destination"], fixture)) for v in model["mappings"]
    ]
    records = []
    for source, dest in mappings:
        # Symlinks are recorded by the online snapshot, but not introduced as writable aliases.
        snapshot = inventory([source])
        require(
            all(row["kind"] != "symlink" for row in snapshot.values()),
            "materialization symlink requires explicit reviewed mapping",
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copyfile(source, dest)
        records.append(dict(source=str(source), destination=str(dest), source_inventory=snapshot))

    readonly = {
        model["runtime"],
        model["runtime"] + "/.venv/bin/python3",
        model["prior_runtime"],
        model["prior_runtime"] + "/.venv/bin/python3",
        *model["executable_dirs"],
    }
    aliases = [(Path(old), relative(new, fixture)) for old, new in model["path_aliases"].items()]

    def mapped(value):
        if type(value) is str and value.startswith("/"):
            if value in readonly:
                return value
            path = Path(value)
            for source, dest in sorted(
                mappings + aliases, key=lambda v: len(str(v[0])), reverse=True
            ):
                if path == source or path.is_relative_to(source):
                    return str(dest / path.relative_to(source))
            return value
        if type(value) is list:
            return [mapped(v) for v in value]
        if type(value) is dict:
            return {k: mapped(v) for k, v in value.items()}
        return value

    for name in model["rewrite_json"]:
        path = relative(name, fixture)
        before = path.read_bytes()
        path.write_text(json.dumps(mapped(json.loads(before))))
        records.append(
            dict(
                rewrite=name,
                original_sha256=hashlib.sha256(before).hexdigest(),
                mapped_sha256=sha(path),
            )
        )
    plist = relative(model["prior_plist"], fixture)
    original = plist.read_bytes()
    plist.write_bytes(plistlib.dumps(mapped(plistlib.loads(original))))
    records.append(
        dict(
            plist=str(plist),
            original_sha256=hashlib.sha256(original).hexdigest(),
            mapped_sha256=sha(plist),
        )
    )
    return fixture, plist, records


def rehearse(root, attempt, phase):
    manifest = json.loads((root / "manifest.json").read_text())
    model = manifest["deployment"]
    writable = root / "payload" / f"attempt-{attempt}"
    area = writable / phase
    area.mkdir(mode=0o700)
    fixture, plist, records = materialize(model, writable)
    python = Path(manifest["python"])
    runtime = Path(model["runtime"])
    real_run = subprocess.run
    # Real read-only git baseline/ancestor proof, still inside kernel isolation.
    baseline_git = []
    for args in (
        ["git", "-C", str(runtime), "rev-parse", "HEAD"],
        [
            "git",
            "-C",
            str(runtime),
            "merge-base",
            "--is-ancestor",
            model["required_feature54"],
            model["head"],
        ],
    ):
        result = real_run(args, capture_output=True, text=True, timeout=30, close_fds=True)
        baseline_git.append(
            dict(argv=args, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        )
        require(result.returncode == 0, "deployment baseline proof failed")
        if "rev-parse" in args:
            require(result.stdout.strip() == model["head"], "runtime exact head drift")
    prior_runtime = Path(model["prior_runtime"])
    checked_plist(
        plist,
        writable,
        prior_runtime / ".venv/bin/python3",
        prior_runtime,
        model["executable_dirs"],
    )
    require(
        sha(plist) == next(v["sha256"] for v in manifest["plists"] if v["role"] == "old"),
        "materialized old plist differs from prevalidated mapping",
    )
    operator = area / "operator"
    operator.mkdir()
    payload = operator / "deploy.py"
    payload.write_bytes(Path(manifest["script"]).read_bytes())
    require(sha(payload) == manifest["script_sha256"], "payload byte identity")
    pointer_paths = [
        fixture / ".pipeline/control" / n
        for n in ("CURRENT_TIMER_DEPLOYMENT.json", "CURRENT_AUTHORIZED_QUEUE.json")
    ]
    pointers = {p: p.read_bytes() for p in pointer_paths}
    prior_plist = plist.read_bytes()
    old = json.loads(pointers[pointer_paths[0]])
    oldcfg = Path(old["config_dir"])
    beneath(str(oldcfg), writable)
    oldconfig = json.loads((oldcfg / "config.json").read_text())
    for path in (
        oldconfig["root"],
        oldconfig["queue"],
        oldconfig["codex_home"],
        oldconfig["merge_policy"]["stop_file"],
        oldconfig["merge_policy"]["merge_log"],
    ):
        beneath(path, writable)
    oldqueue = json.loads(Path(oldconfig["queue"]).read_text())
    for entry in oldqueue["entries"]:
        beneath(entry["control"], writable)
    cfg = fixture / ".pipeline/control" / model["stamp"]
    state = {"loaded": True, "new": False, "runs": 1, "cfgpath": oldcfg / "config.json"}
    clock = [0.0]
    calls = []
    bindings = dict(mode="rehearsal", stamp=model["stamp"], head=model["head"])
    (operator / "bindings.json").write_text(json.dumps(bindings))
    closure = inventory([fixture], strict=True)
    (operator / "deployment-manifest.json").write_text(json.dumps(dict(snapshot_inventory=closure)))

    def validate(*args, **kwargs):
        require(args[0]["snapshot_inventory"] == closure, "fixture manifest identity")
        current = inventory([fixture], strict=True)
        # Only these fixture-local operations are expected from this deployment.
        # This is NOT an exclusion in the full online before/after inventory.
        additions = {str(fixture / name) for name in (".pipeline/snapshots", ".pipeline/work")}
        additions.add(str(Path(oldconfig["root"]) / "wakeup.lock"))
        require(
            set(current) - additions == set(closure) - additions,
            "fixture dependency membership drift",
        )
        for path, before in closure.items():
            require(path in current, "fixture dependency disappeared")
            after = current[path]
            if path in additions:
                continue
            require(
                (before["kind"], before["mode"], before["uid"], before["gid"])
                == (after["kind"], after["mode"], after["uid"], after["gid"]),
                "fixture dependency identity drift",
            )
            if before["kind"] == "file":
                require(before["sha256"] == after["sha256"], "fixture dependency bytes drift")
            else:
                allowed = {Path(v).name for v in additions if Path(v).parent == Path(path)}
                require(
                    set(after["children"]) - allowed == set(before["children"]) - allowed,
                    "fixture directory drift",
                )
        interpreter = (
            prior_runtime / ".venv/bin/python3" if plist.read_bytes() == prior_plist else python
        )
        checked_plist(
            plist,
            writable,
            interpreter,
            prior_runtime if interpreter != python else runtime,
            model["executable_dirs"],
        )
        if kwargs.get("create"):
            for name in (".pipeline/snapshots", ".pipeline/work"):
                (fixture / name).mkdir(parents=True, exist_ok=True)

    def archive(base, expected, tar):
        require(base == fixture and expected == closure, "snapshot fixture binding")
        for name in FILES + (".pipeline/control",):
            tar.add(fixture / name, arcname=name, recursive=True)

    modules = {
        "manifest": types.SimpleNamespace(
            bindings=lambda path: (bindings, fixture, runtime, plist), validate=validate, sha=sha
        ),
        "snapshot_inventory": types.SimpleNamespace(archive=archive),
    }

    def transport(argv, *args, **kwargs):
        calls.append(argv)
        if argv[0] == "launchctl":
            domain = f"gui/{os.getuid()}"
            service = domain + "/com.researchbase.pipeline-wakeup"
            action = argv[1]
            if action == "print-disabled":
                require(argv == ["launchctl", action, domain], "unknown launchd domain")
            elif action == "print":
                require(
                    argv
                    in [
                        ["launchctl", action, domain + "/" + name]
                        for name in (*LEGACY, "com.researchbase.pipeline-wakeup")
                    ],
                    "unknown service",
                )
            elif action in ("bootstrap", "bootout"):
                require(argv == ["launchctl", action, domain, str(plist)], "unknown service plist")
            else:
                require(
                    action in ("enable", "disable") and argv == ["launchctl", action, service],
                    "unknown service action",
                )
            out, rc = "", 0
            if action == "print-disabled":
                out = "\n".join(f'"{n}" => disabled' for n in LEGACY)
            elif action == "print":
                if argv[-1].endswith(LEGACY) or not state["loaded"]:
                    rc = 113
                else:
                    out = f"{state['cfgpath']}\nruns = {state['runs']}\nlast exit code = 0\n"
            elif action == "bootout":
                require(argv[-1] == str(plist), "unknown fixture plist")
                state["loaded"] = False
            elif action == "bootstrap":
                require(argv[-1] == str(plist), "unknown bootstrap plist")
                interpreter = (
                    prior_runtime / ".venv/bin/python3"
                    if plist.read_bytes() == prior_plist
                    else python
                )
                checked_plist(
                    plist,
                    writable,
                    interpreter,
                    prior_runtime if interpreter != python else runtime,
                    model["executable_dirs"],
                )
                spec = plistlib.loads(plist.read_bytes())
                config_path = Path(spec["ProgramArguments"][-1])
                require(
                    config_path in (oldcfg / "config.json", cfg / "config.json"),
                    "unknown bootstrap service",
                )
                # Resolve explicit old/new identity; never inequality=>new.
                state.update(
                    loaded=True, new=config_path == cfg / "config.json", runs=1, cfgpath=config_path
                )
                configuration = json.loads(config_path.read_text())
                for path in (
                    configuration["root"],
                    spec["StandardOutPath"],
                    spec["StandardErrorPath"],
                ):
                    beneath(path, writable)
                Path(spec["StandardOutPath"]).write_text(json.dumps(dict(status="busy")) + "\n")
                Path(spec["StandardErrorPath"]).write_text("")
                state.update(config=configuration, stdout=Path(spec["StandardOutPath"]))
            else:
                require(action in ("disable", "enable"), "unknown launchctl verb")
            return subprocess.CompletedProcess(argv, rc, out, "")
        if argv[0] == "ps":
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[0] == "/opt/homebrew/bin/codex" and argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, model["codex_version"] + "\n", "")
        if argv[0] == "plutil":
            checked_plist(Path(argv[-1]), writable, python, runtime, model["executable_dirs"])
            require(
                sha(Path(argv[-1]))
                == next(v["sha256"] for v in manifest["plists"] if v["role"] == "replacement"),
                "rendered replacement differs from prevalidated plist",
            )
            return subprocess.CompletedProcess(
                argv,
                1 if phase == "rollback" else 0,
                "",
                "injected before install" if phase == "rollback" else "",
            )
        if argv[:4] == ["git", "-C", str(runtime), "rev-parse"] or argv[:4] == [
            "git",
            "-C",
            str(runtime),
            "status",
        ]:
            return real_run(argv, *args, **kwargs)
        if argv[:4] == [str(python), "-m", "scripts.pipeline_wakeup", "--config"]:
            require(
                argv[4] == str(cfg / "config.json") and argv[5] == "--render-plist",
                "render command",
            )
            beneath(argv[6], writable)
            return real_run(argv, *args, **kwargs)
        raise RuntimeError("unknown rehearsal command; real transport forbidden")

    transport._rb_rehearsal_transport = True

    def sleep(seconds):
        clock[0] += seconds
        if state["new"] and clock[0] >= 300 and state["runs"] == 1:
            rows = dict(
                status="checked",
                entries={
                    e["id"]: (
                        "done"
                        if all(
                            t["status"] == "done"
                            for t in json.loads((Path(e["control"]) / "state.json").read_text())[
                                "tasks"
                            ].values()
                        )
                        else "held"
                    )
                    for e in oldqueue["entries"]
                },
                backlog={},
                admission={},
            )
            with state["stdout"].open("a") as stream:
                stream.write(json.dumps(rows) + "\n")
            state["runs"] = 2

    code = 0
    with (
        patch.dict(sys.modules, modules),
        patch("subprocess.run", transport),
        patch("time.sleep", sleep),
        patch("time.monotonic", lambda: clock[0]),
        (area / "transcript.txt").open("w") as transcript,
        contextlib.redirect_stdout(transcript),
    ):
        try:
            runpy.run_path(str(payload), run_name="__main__")
        except SystemExit as error:
            code = error.code
    if phase == "normal":
        require(
            code == 0 and json.loads((operator / "acceptance.json").read_text())["success"],
            "normal deployment rehearsal failed",
        )
    else:
        require(
            code == 2 and json.loads((operator / "rollback.json").read_text())["success"],
            "rollback rehearsal failed",
        )
        require(
            plist.read_bytes() == prior_plist
            and all(p.read_bytes() == raw for p, raw in pointers.items()),
            "prior timer bytes not restored",
        )
    require(sha(payload) == manifest["script_sha256"], "payload modified its source bytes")
    result = dict(
        success=True,
        phase=phase,
        payload_sha256=sha(payload),
        same_payload_bytes=True,
        baseline=model["head"],
        required_feature54=model["required_feature54"],
        launchctl="SIMULATED_ONLY",
        baseline_git=baseline_git,
        clock="SIMULATED_ONLY",
        calls=calls,
        mapping=records,
    )
    (area / "adapter-result.json").write_text(json.dumps(result, sort_keys=True))
    fixture.rename(area / "fixture-result")
    return 0 if phase == "normal" else 23


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--phase", choices=("normal", "rollback"), required=True)
    args = parser.parse_args()
    return rehearse(canonical(args.root), args.attempt, args.phase)


if __name__ == "__main__":
    raise SystemExit(main())
