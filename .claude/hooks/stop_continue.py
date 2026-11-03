#!/usr/bin/env python3
"""Project Stop hook: keep Claude working while .claude/state/pending-tasks.md has open items.

Rules:
- No unchecked "- [ ]" items             -> allow stop, reset counter.
- A line containing "NEEDS_OWNER"         -> allow stop, reset counter (owner decision needed).
- Consecutive block count >= MAX_BLOCKS   -> allow stop, reset counter (loop cap).
- Otherwise                               -> block stop, naming the next open item.
State lives under the project's .claude/state/ (git-ignored).
"""

import json
import os
import re
import sys

CLAUDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(CLAUDE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "pending-tasks.md")
COUNT_FILE = os.path.join(STATE_DIR, "stop-hook-count")
MAX_BLOCKS = 20
UNCHECKED = re.compile(r"^\s*-\s\[ \]\s*(.*)$")


def read_count():
    try:
        with open(COUNT_FILE, "r", encoding="utf-8") as fh:
            return int(fh.read().strip() or "0")
    except (OSError, ValueError):
        return 0


def write_count(value):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(COUNT_FILE, "w", encoding="utf-8") as fh:
            fh.write(str(value))
    except OSError:
        pass


def allow():
    write_count(0)
    sys.exit(0)


def main():
    try:
        sys.stdin.read()  # hook payload is not needed for the decision
    except OSError:
        pass

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        allow()  # no task list means nothing pending

    if any("NEEDS_OWNER" in line for line in lines):
        allow()

    open_items = [m.group(1).strip() for m in (UNCHECKED.match(l) for l in lines) if m]
    if not open_items:
        allow()

    count = read_count()
    if count >= MAX_BLOCKS:
        allow()

    write_count(count + 1)
    reason = (
        f"Unfinished items remain in .claude/state/pending-tasks.md ({len(open_items)} open). "
        f"Continue with the next unchecked item: {open_items[0]}. "
        "When it is done, mark it [x] in that file. If an owner decision is needed, "
        "add a line containing NEEDS_OWNER to that file and explain it in your reply."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
