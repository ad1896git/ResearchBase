"""Read bibliographic exports (BibTeX `.bib`, RIS `.ris`) into plain reference dicts.

Pure parsing: nothing is written, and no network is used. Each reference has the keys
title, authors (list of "First Last" strings), doi, year, journal, volume, issue, pages;
missing values are None. Other BibTeX/RIS fields are ignored.
"""

from __future__ import annotations

import re
from pathlib import Path

REFERENCE_SUFFIXES = frozenset({".bib", ".ris"})
_RIS_LINE = re.compile(r"^([A-Z][A-Z0-9])  - ?(.*)$")
_BIB_FIELD_HEAD = re.compile(r"\s*,?\s*([A-Za-z][\w-]*)\s*=\s*")
_BIB_BARE = re.compile(r"[^,\s}]+")
_BIB_ENTRY_KINDS_SKIPPED = frozenset({"comment", "string", "preamble"})


def _empty() -> dict:
    return {
        "title": None,
        "authors": [],
        "doi": None,
        "year": None,
        "journal": None,
        "volume": None,
        "issue": None,
        "pages": None,
    }


def _clean(value: str) -> str:
    return " ".join(value.replace("{", "").replace("}", "").split())


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I) or None


def _author_name(raw: str) -> str:
    """BibTeX writes "Last, First"; the source material uses "First Last"."""

    if "," in raw:
        last, _, first = raw.partition(",")
        return f"{first.strip()} {last.strip()}".strip()
    return raw.strip()


def _bib_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i, n = 0, len(body)
    while i < n:
        head = _BIB_FIELD_HEAD.match(body, i)
        if head is None:
            i += 1
            continue
        name = head.group(1).lower()
        i = head.end()
        if i < n and body[i] == "{":
            depth, start, value = 0, i + 1, ""
            for j in range(i, n):
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        value, i = body[start:j], j + 1
                        break
            else:
                value, i = body[start:], n
        elif i < n and body[i] == '"':
            end = body.find('"', i + 1)
            end = n if end < 0 else end
            value, i = body[i + 1 : end], end + 1
        else:
            bare = _BIB_BARE.match(body, i)
            value = bare.group(0) if bare else ""
            i = bare.end() if bare else i + 1
        fields[name] = _clean(value)
    return fields


def parse_bibtex(text: str) -> list[dict]:
    references: list[dict] = []
    position = 0
    entry_start = re.compile(r"@\s*([A-Za-z]+)\s*[{(]")
    while True:
        found = entry_start.search(text, position)
        if found is None:
            break
        depth, j = 1, found.end()
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        position = j
        kind = found.group(1).lower()
        if kind in _BIB_ENTRY_KINDS_SKIPPED:
            continue
        body = text[found.end() : j - 1]
        _, _, fields_text = body.partition(",")
        fields = _bib_fields(fields_text)
        reference = _empty()
        reference["title"] = fields.get("title") or None
        reference["authors"] = [
            _author_name(part) for part in re.split(r"\s+and\s+", fields.get("author", "")) if part
        ]
        reference["doi"] = _doi(fields.get("doi"))
        reference["year"] = fields.get("year") or None
        reference["journal"] = fields.get("journal") or fields.get("booktitle") or None
        reference["volume"] = fields.get("volume") or None
        reference["issue"] = fields.get("number") or fields.get("issue") or None
        reference["pages"] = fields.get("pages") or None
        if reference["title"] or reference["doi"]:
            references.append(reference)
    return references


def parse_ris(text: str) -> list[dict]:
    references: list[dict] = []
    current: dict | None = None
    start_page = end_page = None
    for line in text.splitlines():
        match = _RIS_LINE.match(line)
        if match is None:
            continue
        tag, value = match.group(1), match.group(2).strip()
        if tag == "TY":
            current, start_page, end_page = _empty(), None, None
            continue
        if current is None:
            continue
        if tag == "ER":
            current["pages"] = current["pages"] or _pages(start_page, end_page)
            if current["title"] or current["doi"]:
                references.append(current)
            current = None
        elif tag in {"TI", "T1"}:
            current["title"] = current["title"] or value or None
        elif tag in {"AU", "A1"}:
            if value:
                current["authors"].append(_author_name(value))
        elif tag == "DO":
            current["doi"] = current["doi"] or _doi(value)
        elif tag in {"PY", "Y1"}:
            current["year"] = current["year"] or (value[:4] or None)
        elif tag in {"JO", "JF", "JA", "T2"}:
            current["journal"] = current["journal"] or value or None
        elif tag == "VL":
            current["volume"] = value or None
        elif tag == "IS":
            current["issue"] = value or None
        elif tag == "SP":
            start_page = value or None
        elif tag == "EP":
            end_page = value or None
    return references


def _pages(start: str | None, end: str | None) -> str | None:
    if start and end:
        return f"{start}-{end}"
    return start or end


def parse_references(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".bib":
        return parse_bibtex(text)
    return parse_ris(text)
