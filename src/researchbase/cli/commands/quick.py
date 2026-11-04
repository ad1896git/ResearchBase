"""Everyday terminal commands.

Each command completes several steps of the low-level commands (which stay
unchanged). The steps run as the same CLI with --json, so request IDs, the
local owner identity, and validation all behave exactly as in the low-level
commands. Short numbers (1, 2, 3, ...) are resolved in-process through the
Application listing service.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

import typer
from typer.main import get_command

from researchbase.domain.source_identity import IdentifierType, normalize_source_identifier
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..context import CliRuntime
from ..errors import cli_exit_code
from ..output import emit_error
from ..project_context import (
    current_project_id,
    local_root,
    resolve_project,
    set_current_project,
)
from ..transport import add_command, command_group

_TEXT_SUFFIXES = {".txt": "text/plain", ".md": "text/plain", ".xml": "application/jats+xml"}
_PDF_SUFFIX = ".pdf"
_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+")


def _pdf_text(path: Path) -> tuple[str, dict[str, str]]:
    """Extract plain text and document properties from a PDF (pypdf, BSD licence)."""

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "PDF 已加密，无法提取文字：请先取消密码保护"
            )
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        info = reader.metadata or {}
    except PdfReadError as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "无法读取这个 PDF 文件", details={"reason": str(exc)}
        ) from exc
    if not text.strip():
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "PDF 中没有可提取的文字（可能是扫描件）",
            details={"reason": "请先做 OCR 再导入，或改用 .txt 全文"},
        )
    properties = {
        key: str(value).strip()
        for key, value in (("title", info.get("/Title")), ("author", info.get("/Author")))
        if value and str(value).strip()
    }
    return text, properties


def _doi_in(text: str) -> str | None:
    match = _DOI_PATTERN.search(text)
    return match.group(0).rstrip(".,;)]") if match else None


def _refuse_known_doi(project: UUID, doi: str) -> None:
    """Stop before anything is written when this project already has a source with the DOI."""

    try:
        existing = _lo(
            "literature",
            "source",
            "resolve",
            "--project-id",
            str(project),
            "--identifier-type",
            "DOI",
            "--value",
            doi,
        )
    except ResearchBaseError as exc:
        if exc.code is ErrorCode.SOURCE_NOT_FOUND:
            return
        raise
    raise ResearchBaseError(
        ErrorCode.DUPLICATE_CONTENT,
        "这篇文献的 DOI 已登记过，未重复导入",
        details={
            "reason": (
                f"这个 DOI 已登记为「{existing.get('title')}」；"
                "同一 DOI 在一个项目里只保留一条来源记录"
            )
        },
    )


def _valid_doi(doi: str | None) -> str | None:
    """Return the DOI in the same normalized form the identifier commands store, or None.

    Checked before anything is written, so an odd DOI from the PDF text is dropped
    instead of failing the import after the document was already stored.
    """

    if doi is None:
        return None
    try:
        return normalize_source_identifier(IdentifierType.DOI, doi).normalized_value
    except ResearchBaseError:
        return None


# Low-level reasons that need plainer Chinese guidance.
_REASON_HINTS = {
    "quotation not found in source content": "引文在全文中找不到：请逐字复制原文（注意标点和空格）",
    "only planned runs can start": "只有“计划中”的运行才能开始；这个运行已经开始或结束了",
    "only running runs can finish": "只有“运行中”的运行才能结束；请先执行 rb run begin",
    "measurements require a succeeded run": "测量结果只能记在“已成功”的运行上；请先执行 rb run end",
    "evidence relation is already attached": "这条关联已经存在，无需重复添加",
    "current project authority is unavailable": "当前账户无权操作这个项目",
    "exact frozen project document not found": "找不到已冻结的全文，请先执行 rb paper add",
    "document retention/access policy unavailable": "全文缺少保存与访问说明，请重新导入",
    "claim_id is required": "缺少结论编号",
    "invalid CLI input": "输入内容不符合要求，请检查各参数",
    "invalid source version material JSON": "文献版本信息格式不对",
    "supported formats": "目前只支持纯文本（.txt/.md）和 JATS XML 全文",
}


_KIND_LABEL = {
    "question": "研究问题",
    "hypothesis": "假设",
    "experiment": "实验",
    "run": "运行",
    "claim": "结论",
    "paper": "文献",
    "evidence": "文献证据",
    "metric": "度量指标",
    "result": "结果",
    "correction": "更正",
}


def _runtime(ctx: typer.Context) -> CliRuntime:
    return ctx.find_root().obj


def _child_error(stdout: str, stderr: str) -> ResearchBaseError:
    """Turn a failed low-level command into one error with a Chinese reason when possible."""

    for text in (stdout, stderr):
        lines = text.strip().splitlines()
        if not lines:
            continue
        try:
            body = json.loads(lines[-1])
        except json.JSONDecodeError:
            continue
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            try:
                code = ErrorCode(error.get("code"))
            except ValueError:
                code = ErrorCode.VALIDATION_ERROR
            details = error.get("details") or {}
            reason = str(details.get("reason") or error.get("message") or "")
            return ResearchBaseError(code, "操作失败", details=_hint(reason))
    code_match = re.search(r"代码：([A-Z_]+)", stderr)
    try:
        code = ErrorCode(code_match.group(1)) if code_match else ErrorCode.VALIDATION_ERROR
    except ValueError:
        code = ErrorCode.VALIDATION_ERROR
    return ResearchBaseError(code, "操作失败")


def _hint(reason: str) -> dict | None:
    for needle, text in _REASON_HINTS.items():
        if needle in reason:
            return {"reason": text}
    return {"reason": reason} if reason else None


_ROOT_APP: typer.Typer | None = None


def _lo(*args: str) -> dict:
    """Run one low-level command in-process with --json and return its JSON object.

    The same root command tree runs, so request IDs, the local owner identity and
    validation match the low-level commands exactly. Output is captured here.
    """

    if _ROOT_APP is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "命令树尚未初始化")
    command = get_command(_ROOT_APP)
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            # standalone_mode=False returns the exit code instead of exiting.
            # Each high-level call is one new request; the owner never types request IDs.
            request = [] if "--request-id" in args else ["--request-id", str(uuid4())]
            returned = command.main(
                args=[*request, *args, "--json"],
                prog_name="researchbase",
                standalone_mode=False,
            )
            code = int(returned or 0)
        except typer.Exit as exc:
            code = exc.exit_code
        except SystemExit as exc:
            code = int(exc.code or 0)
    if code != 0:
        raise _child_error(out.getvalue(), err.getvalue())
    try:
        return json.loads(out.getvalue())
    except json.JSONDecodeError as exc:
        raise ResearchBaseError(
            ErrorCode.ADAPTER_UNAVAILABLE, "低层命令没有返回可识别的结果"
        ) from exc


def _listing(runtime: CliRuntime) -> Any:
    service = getattr(runtime.services, "record_listing", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "记录列表服务不可用")
    return service


def _resolve(runtime: CliRuntime, project: UUID, kind: str, token: str) -> dict:
    return _listing(runtime).resolve(project, kind, token)


def _row_line(row: dict) -> str:
    title = (row.get("title") or "（无标题）").replace("\n", " ")
    status = row.get("status") or ""
    return f"#{row['short_no']:<3} {title}  [{status}]  {str(row['id'])[:8]}"


def _emit_rows(rows: list[dict], json_mode: bool) -> None:
    if json_mode:
        typer.echo(json.dumps(rows, ensure_ascii=False, default=str))
        return
    if not rows:
        typer.echo("（没有记录）")
        return
    for row in rows:
        typer.echo(_row_line(row))


def _echo_created(label: str, row: dict | None, extra: str = "") -> None:
    number = f"#{row['short_no']} " if row and row.get("short_no") else ""
    typer.echo(f"已添加{label} {number}{extra}".rstrip())


def _ask(value: str | None, label: str) -> str:
    """Use the argument when given; in a terminal ask for it; otherwise say what is missing."""

    if value and value.strip():
        return value.strip()
    if sys.stdin.isatty():
        answer = typer.prompt(label).strip()
        if answer:
            return answer
    raise ResearchBaseError(
        ErrorCode.VALIDATION_ERROR,
        f"缺少{label}",
        details={"reason": f"请在命令后直接写出{label}，或在终端里运行后按提示输入"},
    )


def _ask_or_exit(runtime: CliRuntime, value: str | None, label: str) -> str:
    try:
        return _ask(value, label)
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, False)
        raise typer.Exit(code=cli_exit_code(exc)) from None


def _complete_kind(kind: str):
    """Shell completion for record references: numbers with titles, for the current project."""

    def complete(incomplete: str) -> list[tuple[str, str]]:
        try:
            from ..composition import build_services
            from ..project_context import current_project_id_from_root

            services = build_services()
            credentials = getattr(services, "local_credentials", None)
            listing = getattr(services, "record_listing", None)
            if credentials is None or listing is None:
                return []
            project = current_project_id_from_root(credentials.root)
            if project is None:
                return []
            rows = listing.list(project, kind)
        except Exception:  # completion must never print a traceback into the shell
            return []
        return [
            (str(row["short_no"]), str(row.get("title") or "")[:60])
            for row in rows
            if str(row["short_no"]).startswith(incomplete)
        ]

    return complete


def _run(runtime: CliRuntime, operation) -> None:
    """Run a command body; report stable Chinese errors and exit with the mapped code."""
    try:
        operation()
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, False)
        raise typer.Exit(code=cli_exit_code(exc)) from None


def _group(app: typer.Typer, name: str, help_text: str) -> typer.Typer:
    for info in app.registered_groups:
        if info.name == name and info.typer_instance is not None:
            return info.typer_instance
    group = command_group(help_text)
    app.add_typer(group, name=name)
    return group


# ---- project ---------------------------------------------------------------


def project_use(
    ctx: typer.Context,
    project: Annotated[str, typer.Argument(help="项目 ID（完整 UUID）")],
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project_id = resolve_project(runtime, project)
        set_current_project(runtime, project_id)
        return {"current_project": str(project_id)}

    _show(runtime, operation, lambda r: f"当前项目：{r['current_project']}")


def project_current(ctx: typer.Context) -> None:
    runtime = _runtime(ctx)
    value = current_project_id(runtime)
    typer.echo(
        f"当前项目：{value}" if value else "还没有设置当前项目（researchbase project use <ID>）"
    )


# ---- record kinds ----------------------------------------------------------


def _list_command(kind: str):
    def command(
        ctx: typer.Context,
        keyword: Annotated[str | None, typer.Option("--keyword", "-k")] = None,
        project_id: Annotated[str | None, typer.Option("--project-id")] = None,
        json_mode: bool = typer.Option(False, "--json"),
    ) -> None:
        runtime = _runtime(ctx)
        _run(runtime, lambda: _rows_result(runtime, project_id, kind, keyword, json_mode))

    return command


def _rows_result(runtime, project_id, kind, keyword, json_mode):
    project = resolve_project(runtime, project_id)
    rows = _listing(runtime).list(project, kind, keyword)
    if json_mode:
        return rows
    for row in rows:
        typer.echo(_row_line(row))
    if not rows:
        typer.echo(f"（没有{_KIND_LABEL[kind]}{'匹配“' + keyword + '”' if keyword else ''}）")
    return None


def search(
    ctx: typer.Context,
    keyword: Annotated[str, typer.Argument(help="关键词（匹配标题或陈述）")],
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        listing = _listing(runtime)
        for kind, label in _KIND_LABEL.items():
            rows = listing.list(project, kind, keyword)
            if rows:
                typer.echo(f"[{label}]")
                for row in rows:
                    typer.echo("  " + _row_line(row))
        return None

    _run(runtime, operation)


# ---- questions / hypotheses / experiments / conclusions ---------------------


def question_add(
    ctx: typer.Context,
    text: Annotated[
        str | None, typer.Argument(help="研究问题的文字（可省略，终端中会提示）")
    ] = None,
    scope: Annotated[str | None, typer.Option("--scope")] = None,
    rationale: Annotated[str | None, typer.Option("--rationale")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    text = _ask_or_exit(runtime, text, "研究问题的文字")

    def operation():
        project = resolve_project(runtime, project_id)
        args = ["rq", "create", "--project-id", str(project), "--question-text", text]
        if scope:
            args += ["--scope", scope]
        if rationale:
            args += ["--rationale", rationale]
        created = _lo(*args)
        _lo(
            "rq",
            "freeze",
            "--research-question-id",
            created["id"],
            "--version-id",
            created["current_version_id"],
        )
        row = _resolve(runtime, project, "question", created["id"])
        _echo_created("研究问题", row, text)
        return None

    _run(runtime, operation)


def hypothesis_add(
    ctx: typer.Context,
    question: Annotated[
        str,
        typer.Option(
            "--question", autocompletion=_complete_kind("question"), help="研究问题编号或 ID"
        ),
    ],
    direction: Annotated[str | None, typer.Option("--direction")] = None,
    success: Annotated[str | None, typer.Option("--success")] = None,
    rationale: Annotated[str | None, typer.Option("--rationale")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    statement: Annotated[
        str | None, typer.Argument(help="假设的陈述（可省略，终端中会提示）")
    ] = None,
) -> None:
    runtime = _runtime(ctx)

    statement = _ask_or_exit(runtime, statement, "假设的陈述")

    def operation():
        project = resolve_project(runtime, project_id)
        question_row = _resolve(runtime, project, "question", question)
        args = [
            "hypothesis",
            "create",
            "--project-id",
            str(project),
            "--statement",
            statement,
            "--research-question-id",
            str(question_row["id"]),
        ]
        if direction:
            args += ["--expected-direction", direction]
        if success:
            args += ["--success-criteria", success]
        if rationale:
            args += ["--rationale", rationale]
        created = _lo(*args)
        _lo(
            "hypothesis",
            "freeze",
            "--hypothesis-id",
            created["id"],
            "--version-id",
            created["current_version_id"],
            "--expected-row-version",
            str(created["row_version"]),
        )
        row = _resolve(runtime, project, "hypothesis", created["id"])
        _echo_created("假设", row, statement)
        return None

    _run(runtime, operation)


def experiment_add(
    ctx: typer.Context,
    hypothesis: Annotated[
        str,
        typer.Option(
            "--hypothesis", autocompletion=_complete_kind("hypothesis"), help="假设编号或 ID"
        ),
    ],
    objective: Annotated[str, typer.Option("--objective")],
    protocol: Annotated[str, typer.Option("--protocol")],
    metrics: Annotated[str, typer.Option("--metrics", help="计划测量的指标")],
    seed: Annotated[str, typer.Option("--seed", help="随机种子策略")] = "固定种子 42",
    analysis: Annotated[str, typer.Option("--analysis", help="分析计划")] = "描述性比较",
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
    title: Annotated[str | None, typer.Argument(help="实验名称（可省略，终端中会提示）")] = None,
) -> None:
    runtime = _runtime(ctx)

    title = _ask_or_exit(runtime, title, "实验名称")

    def operation():
        project = resolve_project(runtime, project_id)
        hypothesis_row = _resolve(runtime, project, "hypothesis", hypothesis)
        created = _lo(
            "spec",
            "create",
            "--project-id",
            str(project),
            "--hypothesis-id",
            str(hypothesis_row["id"]),
            "--title",
            title,
            "--objective",
            objective,
            "--protocol",
            protocol,
            "--planned-metrics",
            metrics,
            "--seed-policy",
            seed,
            "--analysis-plan",
            analysis,
        )
        row = _resolve(runtime, project, "experiment", created["id"])
        _echo_created("实验", row, title)
        return None

    _run(runtime, operation)


def conclusion_add(
    ctx: typer.Context,
    statement: Annotated[
        str | None, typer.Argument(help="结论的陈述（可省略，终端中会提示）")
    ] = None,
    scope: Annotated[str | None, typer.Option("--scope")] = None,
    qualification: Annotated[str | None, typer.Option("--qualification")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    statement = _ask_or_exit(runtime, statement, "结论的陈述")

    def operation():
        project = resolve_project(runtime, project_id)
        args = ["claim", "create", "--project-id", str(project), "--statement", statement]
        if scope:
            args += ["--scope", scope]
        if qualification:
            args += ["--qualification", qualification]
        created = _lo(*args)
        row = _resolve(runtime, project, "claim", created["id"])
        _echo_created("结论", row, statement)
        return None

    _run(runtime, operation)


# ---- papers and literature evidence -------------------------------------


def paper_add(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(help="全文文件路径（.pdf / .txt / .md / JATS XML）")],
    title: Annotated[
        str | None, typer.Option("--title", help="标题（默认用 PDF 标题或文件名）")
    ] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        suffix = path.suffix.lower()
        if suffix not in _TEXT_SUFFIXES and suffix != _PDF_SUFFIX:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                f"暂不支持 {suffix or '无扩展名'} 文件",
                details={"reason": "目前支持 PDF / .txt / .md / JATS XML 全文"},
            )
        if not path.is_file():
            raise ResearchBaseError(ErrorCode.NOT_FOUND, f"找不到文件：{path}")
        import_path = path
        media_type = "text/plain" if suffix == _PDF_SUFFIX else _TEXT_SUFFIXES[suffix]
        properties: dict[str, str] = {}
        doi = None
        if suffix == _PDF_SUFFIX:
            text, properties = _pdf_text(path)
            doi = _valid_doi(_doi_in(text))
            if doi:
                _refuse_known_doi(project, doi)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            extracted = local_root(runtime) / "extracted"
            extracted.mkdir(parents=True, exist_ok=True)
            import_path = extracted / f"{digest}.txt"
            import_path.write_text(text, encoding="utf-8")
        label = title or properties.get("title") or path.stem
        document = _lo(
            "literature-evidence",
            "import-document",
            "--project-id",
            str(project),
            "--path",
            str(import_path),
            "--media-type",
            media_type,
            "--rights-basis",
            "个人本地文献，仅用于个人研究记录",
        )
        source_args = [
            "literature",
            "source",
            "create",
            "--project-id",
            str(project),
            "--kind",
            "PAPER",
            "--title",
            label,
        ]
        if doi:
            source_args += ["--initial-identifier-type", "DOI", "--initial-identifier-value", doi]
        source = _lo(*source_args)
        source_id = source["source_id"]
        material = {
            "version_kind": "PUBLISHED",
            "title": label,
            "abstract": None,
            "authors": [],
            "publication_date": None,
            "venue": None,
            "fulltext_artifact": {
                "id": document["artifact_version_id"],
                "content_hash": document["content_hash"],
            },
            "metadata": {
                key: None
                for key in (
                    "journal_identifier",
                    "volume",
                    "issue",
                    "pages",
                    "license_label",
                    "public_repository_label",
                )
            },
        }
        version = _lo(
            "literature",
            "version",
            "create",
            "--project-id",
            str(project),
            "--source-id",
            source_id,
            "--material-json",
            json.dumps(material, ensure_ascii=False),
        )
        _lo(
            "literature",
            "version",
            "freeze",
            "--project-id",
            str(project),
            "--source-version-id",
            version["source_version_id"],
        )
        row = _resolve(runtime, project, "paper", source_id)
        extra = f"（DOI：{doi}）" if doi else ""
        _echo_created("文献", row, label + extra)
        return None

    _run(runtime, operation)


def evidence_verify(
    ctx: typer.Context,
    evidence: Annotated[str, typer.Argument(help="文献证据编号、ID 前缀或引文片段")],
    basis: Annotated[
        str | None, typer.Option("--basis", help="你核对了原文的哪一处、为什么成立")
    ] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        row = _resolve(runtime, project, "evidence", evidence)
        text = _ask(basis, "核验依据（你核对了原文的哪一处）")
        _lo(
            "literature-evidence",
            "review",
            "--project-id",
            str(project),
            "--evidence-id",
            str(row["id"]),
            "--status",
            "VERIFIED",
            "--basis",
            text,
        )
        typer.echo(f"已核验文献证据 #{row['short_no']}（本人核验）")
        return None

    _run(runtime, operation)


_CORRECTION_TYPES = ("factual", "metadata", "computational", "attribution", "other")


def correct(
    ctx: typer.Context,
    conclusion: Annotated[
        str | None,
        typer.Option(
            "--conclusion", autocompletion=_complete_kind("claim"), help="要更正的结论编号"
        ),
    ] = None,
    result: Annotated[
        str | None,
        typer.Option("--result", autocompletion=_complete_kind("result"), help="要更正的结果编号"),
    ] = None,
    assertion: Annotated[
        str | None, typer.Option("--assertion", help="更正后的内容（追加一条更正，原记录保留）")
    ] = None,
    reason: Annotated[str | None, typer.Option("--reason", help="更正原因")] = None,
    correction_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="更正类型：factual / metadata / computational / attribution / other",
        ),
    ] = "factual",
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    """Append a correction to a conclusion or result. Earlier records are never overwritten."""

    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        chosen = [x for x in (conclusion, result) if x]
        if len(chosen) != 1:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "请只指定一个要更正的对象：--conclusion 或 --result",
            )
        kind = correction_type.strip().lower()
        if kind not in _CORRECTION_TYPES:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "更正类型不对",
                details={"reason": "可选：" + " / ".join(_CORRECTION_TYPES), "option": "--type"},
            )
        if conclusion:
            claim_row = _resolve(runtime, project, "claim", conclusion)
            version_id = claim_row.get("version_id")
            if not version_id:
                raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "这个结论还没有版本")
            target_type, target_id, label = "claim_version", str(version_id), "结论"
            target_row = claim_row
        elif result:
            target_row = _resolve(runtime, project, "result", result)
            target_type, target_id, label = "measurement", str(target_row["id"]), "结果"
        else:  # unreachable: exactly one target was checked above
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "请指定要更正的对象")
        text = _ask(assertion, "更正后的内容")
        why = _ask(reason, "更正原因")
        created = _lo(
            "correction",
            "create",
            "--project-id",
            str(project),
            "--target-type",
            target_type,
            "--target-id",
            target_id,
            "--correction-type",
            kind,
            "--corrected-assertion",
            json.dumps(text, ensure_ascii=False),
            "--reason",
            why,
        )
        row = _resolve(runtime, project, "correction", str(created["id"]))
        typer.echo(f"已添加更正 #{row['short_no']}（更正对象：{label} #{target_row['short_no']}）")
        return None

    _run(runtime, operation)


def evidence_add(
    ctx: typer.Context,
    paper: Annotated[
        str,
        typer.Option(
            "--paper", autocompletion=_complete_kind("paper"), help="文献编号、ID 前缀或标题片段"
        ),
    ],
    quote: Annotated[
        str | None, typer.Option("--quote", help="逐字引文（可省略，终端中会提示）")
    ] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    quote = _ask_or_exit(runtime, quote, "逐字引文")

    def operation():
        project = resolve_project(runtime, project_id)
        row = _resolve(runtime, project, "paper", paper)
        detail = _listing(runtime).paper_detail(row["id"], project)
        if not detail or not detail.get("artifact_version_id"):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "这篇文献还没有冻结的全文",
                details={"reason": "请先用 rb paper add 导入全文"},
            )
        created = _lo(
            "literature-evidence",
            "create",
            "--project-id",
            str(project),
            "--source-version-id",
            str(detail["source_version_id"]),
            "--quotation",
            quote,
            "--artifact-version-id",
            str(detail["artifact_version_id"]),
        )
        evidence_row = _resolve(runtime, project, "evidence", created["id"])
        _echo_created("文献证据", evidence_row, quote)
        return None

    _run(runtime, operation)


def claim_link_evidence(
    ctx: typer.Context,
    claim: Annotated[
        str, typer.Option("--claim", autocompletion=_complete_kind("claim"), help="结论编号或 ID")
    ],
    evidence: Annotated[
        str | None,
        typer.Option("--evidence", autocompletion=_complete_kind("evidence"), help="文献证据编号"),
    ] = None,
    measurement: Annotated[
        str | None, typer.Option("--measurement", autocompletion=_complete_kind("result"))
    ] = None,
    statistical: Annotated[str | None, typer.Option("--statistical")] = None,
    relation: Annotated[str, typer.Option("--relation")] = "QUALIFIES",
    note: Annotated[str | None, typer.Option("--note", help="关联说明")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        claim_row = _resolve(runtime, project, "claim", claim)
        version_id = claim_row.get("version_id")
        if not version_id:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "这个结论还没有版本")
        chosen = [x for x in (evidence, measurement, statistical) if x]
        if len(chosen) != 1:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "请只指定一种要关联的内容：--evidence / --measurement / --statistical",
            )
        if evidence:
            if claim_row.get("status") == "DRAFT":
                # Literature support attaches to a frozen claim version.
                _lo(
                    "claim",
                    "freeze",
                    "--claim-id",
                    str(claim_row["id"]),
                    "--version-id",
                    str(version_id),
                )
            evidence_row = _resolve(runtime, project, "evidence", evidence)
            args = [
                "claim",
                "add-evidence",
                "--project-id",
                str(project),
                "--claim-version-id",
                str(version_id),
                "--claim-id",
                str(claim_row["id"]),
                "--literature-evidence-id",
                str(evidence_row["id"]),
                "--relation-type",
                relation.upper(),
            ]
            if note:
                args += ["--qualification", note]
        else:
            args = [
                "claim",
                "add-evidence",
                "--project-id",
                str(project),
                "--claim-version-id",
                str(version_id),
                "--claim-id",
                str(claim_row["id"]),
            ]
            args += ["--expected-row-version", _fresh_version_row(runtime, project, claim_row)]
            if measurement:
                result_row = _resolve(runtime, project, "result", measurement)
                args += ["--measurement-id", str(result_row["id"])]
            else:
                args += ["--statistical-result-id", statistical or ""]
            args += ["--relation-type", relation.lower()]
            if note:
                args += ["--qualification", note]
        _lo(*args)
        typer.echo(f"已关联到结论 #{claim_row['short_no']}")
        return None

    _run(runtime, operation)


def _current(row: dict, kind: str) -> str:
    value = row.get("version_id")
    if not value:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, f"这个{_KIND_LABEL[kind]}还没有版本")
    return str(value)


def _fresh_version_row(runtime: CliRuntime, project: UUID, claim_row: dict) -> str:
    """Claim writes check the claim version row version; read it fresh before writing."""
    fresh = _listing(runtime).resolve(project, "claim", str(claim_row["id"]))
    return str(fresh["version_row_version"])


def _fresh_row_version(runtime: CliRuntime, project: UUID, kind: str, record_id: str) -> str:
    """Read the row version right before writing, so callers never pass it by hand."""
    row = _listing(runtime).resolve(project, kind, record_id)
    return str(row["row_version"])


def metric_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="度量指标名称，如：次日测验平均分")],
    unit: Annotated[str | None, typer.Option("--unit")] = None,
    aggregation: Annotated[str, typer.Option("--aggregation")] = "MEAN",
    definition: Annotated[str | None, typer.Option("--definition")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        args = [
            "metric",
            "create",
            "--project-id",
            str(project),
            "--name",
            name,
            "--definition",
            definition or name,
            "--aggregation",
            aggregation,
        ]
        if unit:
            args += ["--unit", unit]
        created = _lo(*args)
        _lo(
            "metric",
            "freeze",
            "--metric-definition-id",
            created["id"],
            "--version-id",
            created["current_version_id"],
            "--expected-row-version",
            str(created["row_version"]),
        )
        row = _resolve(runtime, project, "metric", created["id"])
        _echo_created("度量指标", row, name)
        return None

    _run(runtime, operation)


def run_add(
    ctx: typer.Context,
    experiment: Annotated[
        str,
        typer.Option(
            "--experiment", autocompletion=_complete_kind("experiment"), help="实验编号或 ID"
        ),
    ],
    run_type: Annotated[str, typer.Option("--type", help="运行类型，如 experiment")] = "experiment",
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        spec = _resolve(runtime, project, "experiment", experiment)
        version_id = _current(spec, "experiment")
        if spec.get("status") == "DRAFT":
            # Runs execute against a frozen experiment version.
            _lo(
                "spec",
                "freeze",
                "--experiment-spec-id",
                str(spec["id"]),
                "--version-id",
                version_id,
                "--expected-row-version",
                str(spec["row_version"]),
            )
        created = _lo(
            "run",
            "create",
            "--project-id",
            str(project),
            "--experiment-spec-version-id",
            version_id,
            "--run-type",
            run_type,
        )
        row = _resolve(runtime, project, "run", created["id"])
        _echo_created("运行", row, f"（{run_type}）")
        return None

    _run(runtime, operation)


def run_start(
    ctx: typer.Context,
    run: Annotated[str, typer.Argument(help="运行编号或 ID")],
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        row = _resolve(runtime, project, "run", run)
        _lo(
            "run",
            "start",
            "--run-id",
            str(row["id"]),
            "--expected-row-version",
            _fresh_row_version(runtime, project, "run", run),
        )
        typer.echo(f"运行 #{row['short_no']} 已开始")
        return None

    _run(runtime, operation)


def run_finish(
    ctx: typer.Context,
    run: Annotated[str, typer.Argument(help="运行编号或 ID")],
    outcome: Annotated[
        str, typer.Option("--outcome", help="SUCCEEDED / FAILED / CANCELLED")
    ] = "SUCCEEDED",
    exit_code: Annotated[int, typer.Option("--exit-code")] = 0,
    failure_reason: Annotated[str | None, typer.Option("--failure-reason")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        row = _resolve(runtime, project, "run", run)
        args = [
            "run",
            "finish",
            "--run-id",
            str(row["id"]),
            "--outcome",
            outcome.upper(),
            "--exit-code",
            str(exit_code),
            "--expected-row-version",
            _fresh_row_version(runtime, project, "run", run),
        ]
        if failure_reason:
            args += ["--failure-reason", failure_reason]
        _lo(*args)
        typer.echo(f"运行 #{row['short_no']} 已结束（{outcome.upper()}）")
        return None

    _run(runtime, operation)


def result_add(
    ctx: typer.Context,
    run: Annotated[
        str, typer.Option("--run", autocompletion=_complete_kind("run"), help="运行编号或 ID")
    ],
    metric: Annotated[
        str,
        typer.Option("--metric", autocompletion=_complete_kind("metric"), help="度量指标编号或 ID"),
    ],
    value: Annotated[str, typer.Option("--value", help="数值")],
    unit: Annotated[str | None, typer.Option("--unit")] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        run_row = _resolve(runtime, project, "run", run)
        metric_row = _resolve(runtime, project, "metric", metric)
        args = [
            "measurement",
            "create",
            "--run-id",
            str(run_row["id"]),
            "--metric-definition-version-id",
            _current(metric_row, "metric"),
            "--numeric-value",
            value,
        ]
        if unit:
            args += ["--unit", unit]
        created = _lo(*args)
        row = _resolve(runtime, project, "result", created["id"])
        _echo_created("结果", row, f"{value}{unit or ''}")
        return None

    _run(runtime, operation)


_EXPORT_KINDS = (
    "question",
    "hypothesis",
    "experiment",
    "metric",
    "run",
    "result",
    "paper",
    "evidence",
    "claim",
    "correction",
)


def export_project(
    ctx: typer.Context,
    out: Annotated[
        Path | None, typer.Option("--out", help="输出文件（默认放在本地配置目录的 exports/ 下）")
    ] = None,
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        from datetime import datetime

        from ..markdown_export import render

        project = resolve_project(runtime, project_id)
        listing = _listing(runtime)
        rows = {kind: listing.list(project, kind) for kind in _EXPORT_KINDS}
        text = render(str(project), rows, listing.claim_links(project), datetime.now())
        if out is None:
            root = local_root(runtime) / "exports"
            target = root / f"project-{str(project)[:8]}.md"
        else:
            target = out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        typer.echo(f"已导出到 {target}")

    _run(runtime, operation)


# ---- registration -----------------------------------------------------------


def _show(runtime: CliRuntime, operation, render) -> None:
    def run():
        typer.echo(render(operation()))

    _run(runtime, run)


def _names(items: list[str], limit: int = 8) -> str:
    shown = "、".join(items[:limit])
    return shown + (f" 等 {len(items)} 个" if len(items) > limit else "")


def folder_scan(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(help="文献文件夹路径")],
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        result = _lo("literature-folder", "scan", "--project-id", str(project), "--path", str(path))
        typer.echo(f"扫描完成：{result['folder']}（共 {result['file_count']} 个文件）")
        if result["new"]:
            typer.echo(f"新增 {len(result['new'])}：{_names(result['new'])}")
        if result["moved"]:
            moves = [f"{item['from']} → {item['to']}" for item in result["moved"]]
            typer.echo(f"移动 {len(result['moved'])}：{_names(moves)}")
        if result["modified"]:
            typer.echo(f"内容已改变 {len(result['modified'])}：{_names(result['modified'])}")
        if result["missing"]:
            typer.echo(f"缺失 {len(result['missing'])}：{_names(result['missing'])}")
        if result["duplicates"]:
            groups = [" = ".join(group) for group in result["duplicates"]]
            typer.echo(f"重复内容 {len(groups)} 组：{_names(groups, 4)}")
        typer.echo(f"未变化 {result['unchanged']} 个")
        return None

    _run(runtime, operation)


def folder_status(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(help="文献文件夹路径")],
    project_id: Annotated[str | None, typer.Option("--project-id")] = None,
) -> None:
    runtime = _runtime(ctx)

    def operation():
        project = resolve_project(runtime, project_id)
        result = _lo(
            "literature-folder", "status", "--project-id", str(project), "--path", str(path)
        )
        typer.echo(f"文件夹：{result['folder']}")
        for item in result["files"]:
            doi = f"  DOI {item['doi']}" if item["doi"] else ""
            title = item["title"] or item["file_path"]
            typer.echo(f"  {item['file_path']}  {title}{doi}")
        if result["missing"]:
            typer.echo(f"已缺失（最近一次扫描未找到）：{_names(result['missing'])}")
        return None

    _run(runtime, operation)


def register(app: typer.Typer) -> None:
    global _ROOT_APP
    _ROOT_APP = app
    project = _group(app, "project", "Project commands.")
    add_command(project, "use", "设置当前项目。", project_use)
    add_command(project, "current", "显示当前项目。", project_current)

    app.command("search", help="在所有记录中按关键词搜索。")(search)
    app.command(
        "export", help="把当前项目导出为 Markdown（问题、假设、实验、结果、文献、结论、更正）。"
    )(export_project)
    app.command("correct", help="更正一条结论或结果：追加更正记录，原记录保留。")(correct)

    question = _group(app, "question", "研究问题命令。")
    add_command(question, "add", "新建研究问题并冻结。", question_add)
    add_command(question, "list", "列出研究问题。", _list_command("question"))

    hypothesis = _group(app, "hypothesis", "Hypothesis commands.")
    add_command(hypothesis, "add", "新建假设（--question 指定研究问题）。", hypothesis_add)
    add_command(hypothesis, "list", "列出假设。", _list_command("hypothesis"))

    experiment = _group(app, "experiment", "实验命令（实验规格）。")
    add_command(experiment, "add", "新建实验（--hypothesis 指定假设）。", experiment_add)
    add_command(experiment, "list", "列出实验。", _list_command("experiment"))

    conclusion = _group(app, "conclusion", "结论命令（即 Claim）。")
    add_command(conclusion, "add", "新建结论。", conclusion_add)
    add_command(conclusion, "list", "列出结论。", _list_command("claim"))

    claim = _group(app, "claim", "Claim and evidence commands.")
    add_command(claim, "add", "新建结论。", conclusion_add)
    add_command(claim, "list", "列出结论。", _list_command("claim"))
    add_command(
        claim, "link-evidence", "把文献证据或测量/统计结果关联到结论。", claim_link_evidence
    )

    metric = _group(app, "metric", "度量指标命令。")
    add_command(metric, "add", "新建并冻结度量指标。", metric_add)
    add_command(metric, "list", "列出度量指标。", _list_command("metric"))

    run_group = _group(app, "run", "Run commands.")
    add_command(run_group, "list", "列出运行。", _list_command("run"))
    add_command(run_group, "add", "为实验新建运行（实验版本未冻结时先冻结）。", run_add)
    add_command(run_group, "begin", "开始运行（底层命令仍为 run start）。", run_start)
    add_command(run_group, "end", "结束运行，--outcome 为 SUCCEEDED/FAILED/CANCELLED。", run_finish)

    result = _group(app, "result", "结果命令（测量值）。")
    add_command(result, "add", "为运行记录一个测量结果。", result_add)
    add_command(result, "list", "列出结果。", _list_command("result"))

    folder = _group(app, "folder", "文献文件夹：扫描、去重、移动检测（只读，不改文件夹）。")
    add_command(folder, "scan", "扫描文献文件夹并记录变化。", folder_scan)
    add_command(folder, "status", "显示文献文件夹最近的状态。", folder_status)
    paper = _group(app, "paper", "文献命令（文件夹之前的简单入口）。")
    add_command(paper, "add", "导入全文并冻结为文献来源版本。", paper_add)
    add_command(paper, "list", "列出文献。", _list_command("paper"))

    evidence = _group(app, "evidence", "文献证据命令。")
    add_command(
        evidence, "verify", "核验文献证据（个人模式可本人核验，导出时会标注）。", evidence_verify
    )
    add_command(evidence, "add", "从文献全文中摘录逐字引文，创建文献证据。", evidence_add)
    add_command(evidence, "list", "列出文献证据。", _list_command("evidence"))
