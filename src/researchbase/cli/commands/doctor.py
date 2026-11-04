"""`rb doctor`: read-only check that full-text records match their stored files."""

from __future__ import annotations

from pathlib import Path

import typer
from sqlalchemy.engine import make_url

from researchbase.foundation.artifact_integrity import (
    PROBLEM_HASH_MISMATCH,
    PROBLEM_INVALID_HASH,
    PROBLEM_MISSING,
    PROBLEM_SIZE_MISMATCH,
    IntegrityReport,
    check_fulltext_records,
)
from researchbase.foundation.doctor_status import default_status_path, write_status
from researchbase.persistence.artifact_integrity import load_fulltext_records
from researchbase.persistence.config import load_settings
from researchbase.persistence.database import create_database_engine

_PROBLEM_TEXT = {
    PROBLEM_INVALID_HASH: "哈希格式无效",
    PROBLEM_MISSING: "文件缺失",
    PROBLEM_HASH_MISMATCH: "文件内容与哈希不一致",
    PROBLEM_SIZE_MISMATCH: "文件大小与记录不一致",
}


def render_report(report: IntegrityReport, database: str | None, store_root: Path) -> list[str]:
    lines = [
        f"数据库：{database}",
        f"全文存储：{store_root}",
        f"检查记录：{report.checked_records} 条（全部全文 artifact 版本），"
        f"涉及 {report.checked_files} 个文件。",
    ]
    if report.ok:
        lines.append("结果：全部正常，每条全文记录都能找到文件且哈希一致。")
        return lines
    lines.append(f"结果：发现 {len(report.problems)} 个问题：")
    for problem in report.problems:
        lines.append(
            f"  - 记录 {problem.artifact_version_id}：{_PROBLEM_TEXT[problem.kind]}"
            f"（哈希 {problem.content_hash[:12]}…）"
        )
    return lines


def register(app: typer.Typer) -> None:
    @app.command(
        "doctor",
        help="检查全文记录能否找到对应文件、哈希是否一致（只读，不修改任何数据）。",
    )
    def doctor(
        record: bool = typer.Option(
            False,
            "--record",
            help="把结果写入状态文件；之后运行任意 rb 命令时会提示存在的问题。",
        ),
    ) -> None:
        settings = load_settings()
        database = make_url(settings.database_url).database
        store_root = Path(settings.artifact_store_root).expanduser()
        engine = create_database_engine(settings.database_url)
        try:
            records = load_fulltext_records(engine)
        finally:
            engine.dispose()
        report = check_fulltext_records(records, store_root)
        for line in render_report(report, database, store_root):
            typer.echo(line)
        if record:
            write_status(
                default_status_path(),
                ok=report.ok,
                records=report.checked_records,
                problems=len(report.problems),
                database=database,
            )
        if not report.ok:
            raise typer.Exit(code=1)
