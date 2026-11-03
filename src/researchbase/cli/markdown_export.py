"""Render one project as Markdown from the listing service's rows and links.

The export is a readable record, not canonical state: it reads the same
short numbers the terminal commands use, so a number in the file can be typed
straight back into `rb ... --paper 3` style commands.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

_STATUS_LABEL = {
    "FROZEN": "已冻结",
    "DRAFT": "草稿",
    "SUPERSEDED": "已被取代",
    "PLANNED": "计划中",
    "RUNNING": "运行中",
    "SUCCEEDED": "已成功",
    "FAILED": "失败",
    "CANCELLED": "已取消",
    "UNREVIEWED": "未审阅",
    "VERIFIED": "已核实",
    "ACTIVE": "有效",
    "RECORDED": "已记录",
}

_RELATION_LABEL = {
    "SUPPORTS": "支持",
    "CONTRADICTS": "反驳",
    "QUALIFIES": "限定",
    "MOTIVATES": "启发",
    "PRIOR_ART": "前人工作",
    "CONTEXTUALIZES": "背景",
    "supports": "支持",
    "contradicts": "反驳",
    "qualifies": "限定",
    "context": "背景",
    "CONTEXT": "背景",
}

_KIND_TITLE = {
    "question": "研究问题",
    "hypothesis": "假设",
    "experiment": "实验",
    "run": "运行",
    "metric": "度量指标",
    "result": "结果",
    "paper": "文献",
    "evidence": "文献证据",
    "claim": "结论",
}


def _status(value: Any) -> str:
    text = str(value or "")
    return _STATUS_LABEL.get(text, text)


def _short(row: dict | None) -> str:
    return f"#{row['short_no']}" if row else "（未关联）"


def _oneline(text: Any) -> str:
    return " ".join(str(text or "（无文字）").split())


def _verifier_mark(row: dict | None) -> str:
    """Owner self-verification is recorded on the review event; the export shows it plainly."""
    return "（本人核验）" if row and row.get("self_verified") else ""


def _entry(indent: str, label: str, row: dict, bold: bool = False) -> str:
    title = _oneline(row.get("title"))
    text = f"{_short(row)} {title}"
    if bold:
        text = f"**{text}**"
    return f"{indent}- {label}{text}（{_status(row.get('status'))}）"


def render(project_id: str, rows: dict[str, list[dict]], links: list[dict], when: datetime) -> str:
    by_id = {kind: {str(r["id"]): r for r in items} for kind, items in rows.items()}
    # Children are keyed by (kind, parent id), e.g. ("experiment", hypothesis id).
    children: dict[tuple[str, str], list[dict]] = defaultdict(list)

    def add_child(kind: str, parent: str | None, row: dict) -> None:
        if parent:
            children[(kind, str(parent))].append(row)

    for row in rows.get("hypothesis", []):
        add_child("hypothesis", row.get("parent_id"), row)
    for row in rows.get("experiment", []):
        add_child("experiment", row.get("parent_id"), row)
    # Runs point at an experiment *version*; map versions back to experiment rows.
    experiment_by_version = {
        str(r["version_id"]): r for r in rows.get("experiment", []) if r.get("version_id")
    }
    for row in rows.get("run", []):
        parent = experiment_by_version.get(str(row.get("parent_id")))
        if parent:
            add_child("experiment_run", str(parent["id"]), row)
    for row in rows.get("result", []):
        add_child("run_result", row.get("parent_id"), row)
    # Evidence points at a source version; map versions back to papers.
    paper_by_version = {
        str(r["version_id"]): r for r in rows.get("paper", []) if r.get("version_id")
    }
    for row in rows.get("evidence", []):
        paper = paper_by_version.get(str(row.get("parent_id")))
        if paper:
            add_child("paper_evidence", str(paper["id"]), row)

    claim_by_version = {
        str(r["version_id"]): r for r in rows.get("claim", []) if r.get("version_id")
    }
    evidence_by_claim: dict[str, list[tuple[str, dict | None, dict]]] = defaultdict(list)
    for link in links:
        claim = claim_by_version.get(str(link["claim_version_id"]))
        if claim is None:
            continue
        target_kind = link["kind"]
        target = None
        if target_kind == "measurement":
            target = by_id.get("result", {}).get(str(link["target_id"]))
        elif target_kind == "literature":
            target = by_id.get("evidence", {}).get(str(link["target_id"]))
        evidence_by_claim[str(claim["id"])].append((target_kind, target, link))

    lines = [
        "# 研究记录导出",
        "",
        f"- 项目 ID：`{project_id}`",
        f"- 导出时间：{when.strftime('%Y-%m-%d %H:%M')}",
        "- 编号（#1、#2…）是项目内的顺序编号，可直接用于终端命令。",
        "",
    ]

    lines += ["## 研究问题与假设", ""]
    questions = sorted(rows.get("question", []), key=lambda r: r["short_no"])
    if not questions:
        lines += ["（没有研究问题）", ""]
    for question in questions:
        lines.append(
            f"- **{_short(question)} {_oneline(question.get('title'))}**"
            f"（{_status(question.get('status'))}）"
        )
        for hypothesis in children.get(("hypothesis", str(question["id"])), []):
            lines.append(_entry("  ", "假设 ", hypothesis))
            for experiment in children.get(("experiment", str(hypothesis["id"])), []):
                lines.append(_entry("    ", "实验 ", experiment))
                for run in children.get(("experiment_run", str(experiment["id"])), []):
                    lines.append(_entry("      ", "运行 ", run))
                    for result in children.get(("run_result", str(run["id"])), []):
                        lines.append(
                            f"        - 结果 {_short(result)} {_oneline(result.get('title'))}"
                        )
    lines.append("")

    lines += ["## 度量指标", ""]
    metrics = sorted(rows.get("metric", []), key=lambda r: r["short_no"])
    if not metrics:
        lines += ["（没有度量指标）", ""]
    for metric in metrics:
        lines.append(
            f"- {_short(metric)} {_oneline(metric.get('title'))}（{_status(metric.get('status'))}）"
        )
    lines.append("")

    lines += ["## 文献与引文", ""]
    papers = sorted(rows.get("paper", []), key=lambda r: r["short_no"])
    if not papers:
        lines += ["（没有文献）", ""]
    for paper in papers:
        lines.append(
            f"- {_short(paper)} {_oneline(paper.get('title'))}（{_status(paper.get('status'))}）"
        )
        for evidence in children.get(("paper_evidence", str(paper["id"])), []):
            quote = _oneline(evidence.get("title"))
            lines.append(f"  - 引文 {_short(evidence)}：「{quote}」{_verifier_mark(evidence)}")
    lines.append("")

    lines += ["## 结论与证据", ""]
    claims = sorted(rows.get("claim", []), key=lambda r: r["short_no"])
    if not claims:
        lines += ["（没有结论）", ""]
    for claim in claims:
        lines.append(_entry("", "", claim, bold=True))
        for target_kind, target, link in evidence_by_claim.get(str(claim["id"]), []):
            relation = _RELATION_LABEL.get(str(link["relation_type"]), str(link["relation_type"]))
            if target_kind == "literature":
                quote = _oneline(target.get("title")) if target else ""
                shown = f"文献证据 {_short(target)}：「{quote}」{_verifier_mark(target)}"
            elif target_kind == "measurement":
                shown = (
                    f"测量结果 {_short(target)} {_oneline(target.get('title')) if target else ''}"
                )
            else:
                shown = "统计结果（未在列表中展示）"
            note = (
                f"；说明：{_oneline(link.get('qualification'))}"
                if link.get("qualification")
                else ""
            )
            lines.append(f"  - {relation}：{shown}{note}")
    lines.append("")

    lines += ["## 参考文献", ""]
    if not papers:
        lines += ["（没有文献）", ""]
    for paper in papers:
        lines.append(f"{_short(paper)}. {_oneline(paper.get('title'))}")
    lines.append("")
    return "\n".join(lines)
