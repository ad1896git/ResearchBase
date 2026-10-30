"""Bounded fresh Codex sessions; no resume, ambient plugins or remote publication."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from scripts.pipeline_protocol import atomic_write, encoded, require

SCRIPTS = Path(__file__).resolve().parent


def group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Unknown group membership is not proof of termination.


def stop_group(pgid: int, reap=lambda: None) -> bool:
    def alive():
        reap()
        return group_alive(pgid)

    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not alive():
            return True
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        end = time.monotonic() + 1
        while alive() and time.monotonic() < end:
            time.sleep(0.05)
    return not alive()


def run_session(
    cwd: Path,
    output: Path,
    prompt: str,
    schema: Path,
    *,
    writable=False,
    timeout=180,
    codex="codex",
) -> dict:
    """Caller owns its control lock. A launch marker without terminal receipt denies replay."""
    require(1 <= timeout <= 600, "session timeout out of bounds")
    output.mkdir(exist_ok=False)
    atomic_write(output / "prompt.txt", prompt.encode())
    atomic_write(output / "schema.json", schema.read_bytes())
    argv = [
        codex,
        "exec",
        "--ignore-user-config",
        "--strict-config",
        "--ephemeral",
        "--json",
        "--sandbox",
        "workspace-write" if writable else "read-only",
        "-c",
        'approval_policy="never"',
        "-c",
        "sandbox_workspace_write.writable_roots=[]",
        "-c",
        "sandbox_workspace_write.exclude_slash_tmp=true",
        "-c",
        "sandbox_workspace_write.exclude_tmpdir_env_var=true",
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-C",
        str(cwd),
        "--output-schema",
        str(output / "schema.json"),
        "--output-last-message",
        str(output / "answer.json"),
        "-",
    ]
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        in (
            "PATH",
            "HOME",
            "USER",
            "LOGNAME",
            "TMPDIR",
            "CODEX_HOME",
            "LANG",
            "LC_ALL",
        )
    }
    if writable:
        # Temp space stays inside the already writable checkout, never in control.
        scratch = Path(tempfile.mkdtemp(prefix=".pipeline-session-", dir=cwd.resolve()))
        env["TMPDIR"] = str(scratch)
        env["TMPPREFIX"] = str(scratch / "zsh")
        for key in ("TMPDIR", "TMPPREFIX"):
            argv.extend(["-c", f"shell_environment_policy.set.{key}={json.dumps(env[key])}"])
        # Options must precede the stdin prompt argument.
        argv.remove("-")
        argv.append("-")
        atomic_write(output / "scratch.json", encoded({"path": str(scratch)}))
    atomic_write(output / "launch.json", encoded({"argv": argv, "timeout": timeout}))
    with (
        (output / "events.jsonl").open("xb") as stdout,
        (output / "stderr.log").open("xb") as stderr,
    ):
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        atomic_write(output / "process.json", encoded({"pid": process.pid, "pgid": process.pid}))
        timed_out = False
        try:
            process.communicate(prompt.encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_group(process.pid, process.poll)
            process.wait(timeout=3)
        finally:
            stopped = stop_group(process.pid, process.poll)
        receipt = dict(
            exit_code=process.returncode,
            timed_out=timed_out,
            descendants_stopped=stopped,
        )
        atomic_write(output / "terminal.json", encoded(receipt))
        return receipt
