import json
import time

from scripts.pipeline_sessions import SCRIPTS, run_session


def test_timeout_terminates_actual_process_group(tmp_path):
    program = tmp_path / "fake-codex"
    program.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n")
    program.chmod(0o700)
    start = time.monotonic()
    receipt = run_session(
        tmp_path,
        tmp_path / "session",
        "bounded",
        SCRIPTS / "pipeline_commander.schema.json",
        codex=str(program),
        timeout=1,
    )
    assert receipt["timed_out"] and receipt["exit_code"] != 0
    assert receipt["descendants_stopped"]
    assert time.monotonic() - start < 7
    saved = json.loads((tmp_path / "session" / "launch.json").read_text())
    assert "--output-schema" in saved["argv"] and "resume" not in saved["argv"]


def test_temporary_control_does_not_grant_temporary_write_roots(tmp_path):
    program = tmp_path / "fake-codex"
    program.write_text("#!/usr/bin/env python3\n")
    program.chmod(0o700)
    output = tmp_path / "control-under-temp"
    run_session(
        tmp_path,
        output,
        "bounded",
        SCRIPTS / "pipeline_result.schema.json",
        writable=True,
        codex=str(program),
        timeout=2,
    )
    argv = json.loads((output / "launch.json").read_text())["argv"]
    assert "--strict-config" in argv
    assert "sandbox_workspace_write.writable_roots=[]" in argv
    assert "sandbox_workspace_write.exclude_slash_tmp=true" in argv
    assert "sandbox_workspace_write.exclude_tmpdir_env_var=true" in argv
    assert "sandbox_workspace_write.network_access=false" in argv
