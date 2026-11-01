"""Read-only inventory of durable notification events; never infer live task state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MAX_EVENTS = 10000
MAX_BYTES = 65536


def inventory(folder: Path) -> dict:
    """Fail visibly on corrupt, unsafe or incomplete event inventories."""
    if not folder.is_absolute() or folder.resolve() != folder or not folder.is_dir():
        raise ValueError("notification directory must be canonical, absolute and present")
    files = sorted(folder.iterdir())
    if len(files) > MAX_EVENTS:
        raise ValueError("notification inventory limit exceeded; no partial report")
    counts: dict[str, int] = {}
    events = []
    for path in files:
        if (
            not re.fullmatch(r"[0-9a-f]{64}\.json", path.name)
            or path.is_symlink()
            or not path.is_file()
        ):
            raise ValueError(f"unexpected notification entry: {path.name}")
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("notification event too large")
        if hashlib.sha256(data).hexdigest() != path.stem:
            raise ValueError("notification digest mismatch")
        value = json.loads(data)
        if type(value) is not dict or type(value.get("status")) is not str or not value["status"]:
            raise ValueError("notification event lacks a status")
        status = value["status"]
        counts[status] = counts.get(status, 0) + 1
        events.append(dict(event_file=path.name, notification=value))
    # A snapshot of event filenames cannot prove a task's current state. Detect
    # concurrent arrivals rather than silently presenting an incomplete inventory.
    if sorted(folder.iterdir()) != files:
        raise ValueError("notification directory changed; retry read-only inventory")
    return dict(
        kind="historical_notification_inventory",
        live_task_state_verified=False,
        event_count=len(events),
        counts=counts,
        events=events,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = inventory(args.directory)
    except (OSError, ValueError) as exc:
        print(json.dumps(dict(status="blocked", reason=str(exc))), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
