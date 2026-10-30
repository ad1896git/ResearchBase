"""Preview (default) or install the two safety fixes into the known legacy driver.

Stop all legacy loops before --apply. No process, lane, state or DB is removed.
Unknown driver revisions fail closed; this is not a general source rewriter.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import stat
import tempfile
from pathlib import Path

from scripts.pipeline_safety import ProcessLock, SafetyError

LEGACY_HASH = "fb700f8947b77d59aeb98cd134980ea56cd39866c6ae779d28223d482e903203"
LOOP_HASH = "8cfc7009386ad1f142db06796ff11ff5d4dc408777ff834dee384a3afaf50213"
PREPARE = """def prepare_lane(step):
    return safe_prepare_lane(REPO, PIPE / "work", step)"""
TAKE_LOCK = """def take_lock():
    if not _process_lock.acquire():
        log("another autopilot holds the kernel lock; exiting")
        return False
    begin_legacy_run(LOGS / "autopilot.active")
    PIDFILE.write_text(str(os.getpid()))
    return True"""
LOOP = """#!/bin/sh
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
PIPELINE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
exec python3 "$PIPELINE_DIR/../scripts/pipeline_safety.py" --pipeline "$PIPELINE_DIR"
"""


def transformed(original: bytes) -> bytes:
    if hashlib.sha256(original).hexdigest() != LEGACY_HASH:
        raise SafetyError("unknown legacy driver; review it before installation")
    return _rewrite(original.decode()).encode()


def _rewrite(text: str) -> str:
    lines = text.splitlines(keepends=True)
    replacements = {"prepare_lane": PREPARE, "take_lock": TAKE_LOCK}
    for node in reversed(ast.parse(text).body):
        if isinstance(node, ast.FunctionDef) and node.name in replacements:
            lines[node.lineno - 1 : node.end_lineno] = [replacements[node.name] + "\n"]
    text = "".join(lines)
    anchor = 'DB_BASE = "postgresql+psycopg://researchbase:researchbase@localhost:5432"\n'
    text = text.replace(
        anchor,
        anchor + '\nsys.path.insert(0, str(REPO / "scripts"))\n'
        "from pipeline_safety import (ProcessLock, prepare_lane as safe_prepare_lane, "
        "begin_legacy_run, finish_legacy_run)\n"
        '_process_lock = ProcessLock(LOGS / "autopilot.lock")\n',
        1,
    )
    # State reads/reset must happen after the lock, not in the former race window.
    reset = """    state = load_state()
    if a.reset:
        state["steps"].pop(a.reset, None)
        save_state(state)
"""
    assert text.count(reset) == 1
    text = text.replace(reset, "", 1)
    marker = "    if not take_lock():\n        return 0\n"
    assert text.count(marker) == 1
    text = text.replace(marker, marker + reset, 1)
    successful_exit = '    if rc == 0:\n        log("queue waiting for explicit disposition"'
    assert text.count(successful_exit) == 1
    text = text.replace(
        successful_exit,
        '    if rc == 0:\n        finish_legacy_run(LOGS / "autopilot.active")\n'
        '        log("queue waiting for explicit disposition"',
        1,
    )
    ast.parse(text)
    return text


def atomic_write(path: Path, data: bytes):
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, name = tempfile.mkstemp(prefix=".safety-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install(root: Path, *, apply: bool = False) -> dict[str, str]:
    pipeline = root / ".pipeline"
    driver = pipeline / "bin/autopilot.py"
    loop = pipeline / "bin/run_forever.sh"
    original = driver.read_bytes()
    patched = transformed(original)
    if hashlib.sha256(loop.read_bytes()).hexdigest() != LOOP_HASH:
        raise SafetyError("unknown legacy loop; review it before installation")
    result = {"autopilot.py": hashlib.sha256(patched).hexdigest(), "run_forever.sh": "replaced"}
    if not apply:
        return result
    for name in ("autopilot.pid", "autopilot_background_resume.pid"):
        pidfile = pipeline / "logs" / name
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text().strip()), 0)
            except ProcessLookupError:
                pass
            else:
                raise SafetyError("recorded legacy process may be alive; stop and verify first")
    with (
        ProcessLock(pipeline / "logs/runner.lock"),
        ProcessLock(pipeline / "logs/autopilot.lock"),
    ):
        backup = pipeline / "logs/safety-backup"
        backup.mkdir(exist_ok=True)
        for path, content in ((driver, patched), (loop, LOOP.encode())):
            saved = backup / (path.name + ".before")
            with saved.open("xb") as stream:
                stream.write(path.read_bytes())
            atomic_write(path, content)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(install(args.root.resolve(), apply=args.apply))
