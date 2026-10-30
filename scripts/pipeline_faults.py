"""Conservative classification from host-owned terminal and raw session evidence."""

import json
from pathlib import Path


def classify(output: Path, terminal: dict) -> str | None:
    if terminal.get("descendants_stopped") is not True:
        return None
    messages = []
    events = output / "events.jsonl"
    if events.is_file() and not events.is_symlink():
        for line in events.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                return None
            if type(row) is not dict:
                return None
            item = row.get("item", {})
            if type(item) is dict:
                messages.append(str(item.get("aggregated_output", "")))
            if row.get("type") in ("error", "turn.failed"):
                messages.append(json.dumps(row))
    stderr = output / "stderr.log"
    if stderr.is_file() and not stderr.is_symlink():
        messages.append(stderr.read_text())
    diagnostic = "\n".join(messages).lower()
    if any(
        x in diagnostic
        for x in (
            "operation not permitted",
            "permission denied",
            "invalid schema",
            "output schema",
            "no such file or directory",
            "read-only file system",
            "failed to write",
            "unknown variant",
            "invalid configuration",
            "os error 13",
            "os error 30",
            "schema validation",
            "unexpected argument",
            "failed to parse configuration",
            "invalid type:",
        )
    ):
        return None
    if any(
        x in diagnostic
        for x in ("usage limit", "quota exceeded", "insufficient_quota", "rate limit", "rate_limit")
    ):
        return "quota"
    if terminal.get("timed_out") is True:
        return "timeout"
    exit_code = terminal.get("exit_code")
    if type(exit_code) is int and exit_code != 0:
        if exit_code < 0 or any(
            x in diagnostic
            for x in (
                "stream disconnected",
                "connection reset",
                "connection timed out",
                "network is unreachable",
                "session interrupted",
                "unexpected eof",
            )
        ):
            return "session_exit"
    return None
