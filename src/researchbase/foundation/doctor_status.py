"""Persisted result of the last `rb doctor --record` run.

Later `rb` commands read this file to show a warning. Reading never raises:
a missing or unreadable file means no warning.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def default_status_path() -> Path:
    override = os.environ.get("RESEARCHBASE_DOCTOR_STATUS")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".researchbase" / "doctor-status.json"


def write_status(
    path: Path, *, ok: bool, records: int, problems: int, database: str | None
) -> None:
    payload = {
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ok": ok,
        "records": records,
        "problems": problems,
        "database": database,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def pending_warning(path: Path) -> str | None:
    """Return a Chinese warning when the last recorded check found problems."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("ok") is not False:
        return None
    problems = payload.get("problems")
    checked_at = payload.get("checked_at", "未知时间")
    count = problems if isinstance(problems, int) and problems > 0 else 1
    return f"提示：全文完整性检查（{checked_at}）发现 {count} 个问题。请运行 rb doctor 查看详情。"
