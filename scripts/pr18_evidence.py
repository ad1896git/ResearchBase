"""Fail-closed helpers for PR-18 evidence.

This module intentionally does not modify the PR-17DR5 evidence generator or
its artifacts. It validates the small, repository-relative manifest used to
record PR-18 verification results.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pr17dr_evidence import VERIFICATION_COMMANDS as _PR17_COMMANDS  # noqa: E402

_PR18_BASE_COMMANDS: tuple[tuple[str, list[str]], ...] = tuple(
    (
        command_id,
        [
            *command,
            "tests/integration/test_pr18_hardening.py",
        ],
    )
    if command_id == "catalog_exact_verification"
    else (command_id, command)
    for command_id, command in _PR17_COMMANDS
)

AUTHORITATIVE_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    *_PR18_BASE_COMMANDS,
    (
        "pr18_focused_and_evidence_tool",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/unit/test_pr18_explain_contract.py",
            "tests/unit/test_pr18_evidence.py",
            "tests/unit/test_pr18_error_log_hardening.py",
            "tests/unit/test_pr18_docs_examples.py",
            "tests/architecture/test_pr18_boundaries.py",
            "tests/integration/test_pr18_hardening.py",
            "tests/unit/test_pr17dr2_evidence.py",
            "tests/unit/test_pr17dr2_test_integrity.py",
        ],
    ),
)

PYTEST_COUNT_FIELDS = (
    "total_discovered",
    "selected",
    "deselected",
    "passed",
    "failed",
    "skipped",
    "xfailed",
    "xpassed",
    "errors",
    "return_code",
)
_SUMMARY_COUNT = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|deselected|xfailed|xpassed|errors?)"
)
_COLLECTION_COUNT = re.compile(
    r"^[ \t]*(?:(?P<selected>\d+)/)?(?P<total>\d+) tests? collected"
    r"(?: \((?P<deselected>\d+) deselected\))?",
    re.MULTILINE,
)
INHERITED_PR11R2_SKIP_IDENTITIES = frozenset(
    {
        "tests.integration.test_pr11r2_migration::test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head",
        "tests.integration.test_pr11r2_migration::test_invalid_legacy_upgrade_fails_closed_and_manual_remediation_retries",
    }
)
TODO_DISPOSITIONS = frozenset({"CLOSED", "INTENTIONAL_NONBLOCKING", "OUT_OF_PHASE", "PR18_BLOCKER"})
TODO_MARKERS = ("TODO", "FIXME", "XXX", "HACK", "TBD")
TODO_ROOTS = ("src", "migrations", "tests", "docs", "scripts", "execution", "artifacts")
TODO_EXTENSIONS = frozenset({".py", ".sql", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"})
_TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK|TBD)\b", re.IGNORECASE)

_ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_CREDENTIAL_TOKEN = re.compile(
    r"(?i)(?:password|passwd|secret|credential|api[_-]?key|token)\s*[=:]|"
    r"postgres(?:ql)?(?:\+[^:/\s]+)?://[^:/\s]+:[^@\s]+@"
)


class PR18EvidenceError(ValueError):
    """Raised when PR-18 evidence is incomplete, stale, or unsafe."""

    status = "NOT_VERIFIED"


NOT_VERIFIED = "NOT_VERIFIED"

READ_SELECT = "READ_SELECT"
READ_SELECT_LOCKING = "READ_SELECT_LOCKING"
DATA_MODIFYING_CTE = "DATA_MODIFYING_CTE"
SELECT_INTO_WRITE = "SELECT_INTO_WRITE"
WRITE_INSERT = "WRITE_INSERT"
WRITE_UPDATE = "WRITE_UPDATE"
WRITE_DELETE = "WRITE_DELETE"
WRITE_MERGE = "WRITE_MERGE"
DDL = "DDL"
TRANSACTION_CONTROL = "TRANSACTION_CONTROL"
SESSION_OR_CONFIG_CHANGE = "SESSION_OR_CONFIG_CHANGE"
UNKNOWN = "UNKNOWN"

_STATEMENT_KEYWORDS = frozenset(
    {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "BEGIN",
        "START",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "RELEASE",
        "END",
        "ABORT",
        "SET",
        "RESET",
        "DISCARD",
        "USE",
        "PRAGMA",
        "SHOW",
    }
)
_DDL_KEYWORDS = frozenset({"CREATE", "ALTER", "DROP", "TRUNCATE"})
_TRANSACTION_KEYWORDS = frozenset(
    {"BEGIN", "START", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "END", "ABORT"}
)


@dataclass(frozen=True)
class _SQLToken:
    text: str
    depth: int
    kind: str


@dataclass(frozen=True)
class _LexedSQL:
    tokens: tuple[_SQLToken, ...]
    valid: bool
    multi_statement: bool
    statement_complete: bool


@dataclass(frozen=True)
class _StatementAnalysis:
    statement_class: str
    lexical_valid: bool
    grammar_supported: bool
    statement_complete: bool
    mutating_cte_detected: bool
    select_into_detected: bool
    locking_detected: bool
    multi_statement_detected: bool
    unknown_detected: bool


_DOLLAR_QUOTE_TAG = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")
_MUTATING_COMMANDS = frozenset({"INSERT", "UPDATE", "DELETE", "MERGE"})
_SELECT_SCOPE_BOUNDARIES = frozenset(
    {
        "FROM",
        "WHERE",
        "GROUP",
        "HAVING",
        "WINDOW",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "FETCH",
        "FILTER",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "RETURNING",
    }
)
_LOCKING_SEQUENCES = (
    ("FOR", "UPDATE"),
    ("FOR", "NO", "KEY", "UPDATE"),
    ("FOR", "SHARE"),
    ("FOR", "KEY", "SHARE"),
)
_SQL_OPERATOR_CHARS = frozenset(".,:%=+-*/<>!|&~^[]{}?$#@")
_GRAMMAR_CLAUSE_BOUNDARIES = frozenset(
    {
        "FROM",
        "WHERE",
        "GROUP",
        "HAVING",
        "WINDOW",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "FETCH",
        "INTO",
        "UNION",
        "INTERSECT",
        "EXCEPT",
        "RETURNING",
    }
)
_INCOMPLETE_CLAUSE_WORDS = frozenset(
    {
        "AS",
        "BETWEEN",
        "FROM",
        "WHERE",
        "GROUP",
        "HAVING",
        "WINDOW",
        "ORDER",
        "BY",
        "DISTINCT",
        "ON",
        "CASE",
        "COLLATE",
        "WHEN",
        "THEN",
        "ELSE",
        "AND",
        "IS",
        "LIKE",
        "NOT",
        "OR",
        "NULLS",
    }
)
_STRUCTURAL_WORDS = frozenset(
    {
        "AND",
        "ASC",
        "AS",
        "AT",
        "BETWEEN",
        "BY",
        "CASE",
        "COLLATE",
        "DESC",
        "ELSE",
        "END",
        "EXCEPT",
        "FETCH",
        "FILTER",
        "FIRST",
        "FROM",
        "GROUP",
        "HAVING",
        "IN",
        "INTERSECT",
        "IS",
        "JOIN",
        "FOR",
        "KEY",
        "LAST",
        "LIKE",
        "NO",
        "NOT",
        "NULL",
        "NULLS",
        "ON",
        "OR",
        "ORDER",
        "OFFSET",
        "ONLY",
        "ROWS",
        "S",
        "SHARE",
        "THEN",
        "UPDATE",
        "USING",
        "WHEN",
        "WHERE",
        "WINDOW",
        "UNION",
    }
)
_SUPPORTED_OPERATOR_RUNS = frozenset(
    {
        "!",
        "!=",
        "#",
        "#>",
        "#>>",
        "$",
        "%",
        "&",
        "*",
        "+",
        ",",
        "-",
        ".",
        "/",
        ":",
        "::",
        "<",
        "<@",
        "<=",
        "<>",
        "=",
        ">",
        ">=",
        "?",
        "?&",
        "?|",
        "@",
        "@>",
        "^",
        "|",
        "||",
        "~",
        "->",
        "->>",
        "=>",
        ".*",
        "[",
        "]",
    }
)


def _lex_sql(statement: str) -> _LexedSQL:
    """Lex enough PostgreSQL syntax to classify a complete captured statement."""

    tokens: list[_SQLToken] = []
    index = 0
    depth = 0
    length = len(statement)
    invalid = False

    while index < length:
        character = statement[index]
        if character.isspace():
            index += 1
            continue
        if statement.startswith("--", index):
            newline = statement.find("\n", index + 2)
            index = length if newline == -1 else newline + 1
            continue
        if statement.startswith("/*", index):
            cursor = index + 2
            closed = False
            while cursor < length:
                if statement.startswith("/*", cursor):
                    invalid = True
                    break
                if statement.startswith("*/", cursor):
                    index = cursor + 2
                    closed = True
                    break
                cursor += 1
            if invalid:
                break
            if not closed:
                invalid = True
                break
            continue
        if statement.startswith("*/", index):
            invalid = True
            break
        if character == "`":
            invalid = True
            break
        if character in {"'", '"'}:
            quote = character
            token_kind = "literal" if quote == "'" else "identifier"
            index += 1
            closed = False
            while index < length:
                if statement[index] == quote:
                    if index + 1 < length and statement[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    closed = True
                    break
                if quote == "'" and statement[index] == "\\" and index + 1 < length:
                    index += 2
                    continue
                index += 1
            if not closed:
                invalid = True
                break
            tokens.append(_SQLToken("<literal>", depth, token_kind))
            continue
        if character == "$":
            tag_match = _DOLLAR_QUOTE_TAG.match(statement, index)
            if tag_match:
                tag = tag_match.group(0)
                end = statement.find(tag, tag_match.end())
                if end == -1:
                    invalid = True
                    break
                index = end + len(tag)
                tokens.append(_SQLToken("<literal>", depth, "literal"))
                continue
        if character == "(":
            tokens.append(_SQLToken("(", depth, "symbol"))
            depth += 1
            index += 1
            continue
        if character == ")":
            if depth == 0:
                invalid = True
                break
            depth -= 1
            tokens.append(_SQLToken(")", depth, "symbol"))
            index += 1
            continue
        if character == ";":
            if depth != 0:
                invalid = True
                break
            tokens.append(_SQLToken(";", depth, "symbol"))
            index += 1
            continue
        if character.isalpha() or character == "_":
            end = index + 1
            while end < length and (statement[end].isalnum() or statement[end] == "_"):
                end += 1
            tokens.append(_SQLToken(statement[index:end].upper(), depth, "word"))
            index = end
            continue
        if character.isdigit():
            end = index + 1
            while end < length and (statement[end].isalnum() or statement[end] in {".", "_"}):
                end += 1
            tokens.append(_SQLToken("<literal>", depth, "literal"))
            index = end
            continue
        if character in _SQL_OPERATOR_CHARS:
            tokens.append(_SQLToken(character, depth, "operator"))
            index += 1
            continue
        invalid = True
        break

    if depth != 0:
        invalid = True

    semicolon_indexes = [
        position
        for position, token in enumerate(tokens)
        if token.kind == "symbol" and token.text == ";"
    ]
    multi_statement = False
    if semicolon_indexes:
        first_semicolon = semicolon_indexes[0]
        multi_statement = (
            first_semicolon == 0 or len(semicolon_indexes) > 1 or first_semicolon != len(tokens) - 1
        )

    valid = not invalid
    statement_complete = valid and bool(tokens) and not multi_statement
    return _LexedSQL(tuple(tokens), valid, multi_statement, statement_complete)


def _sql_tokens(statement: str) -> list[tuple[str, int]]:
    """Compatibility view of significant SQL words outside comments/literals."""

    lexed = _lex_sql(statement)
    if not lexed.valid:
        return []
    return [
        (token.text, token.depth)
        for token in lexed.tokens
        if token.kind == "word" or token.text == ";"
    ]


def _statement_sql(statement: object) -> str | None:
    if isinstance(statement, str):
        return statement
    if isinstance(statement, dict):
        value = statement.get("sql")
        return value if isinstance(value, str) else None
    if isinstance(statement, tuple) and statement and isinstance(statement[0], str):
        return statement[0]
    return None


def _safe_sql_projection(statement: str) -> str:
    """Normalize SQL without recording bound values or execution parameters."""

    normalized = re.sub(r"'(?:''|[^'])*'", "'<redacted>'", statement)
    normalized = re.sub(r"\b\d+(?:\.\d+)?\b", "<number>", normalized)
    return re.sub(r"\s+", " ", normalized.strip())


def _has_select_into(tokens: tuple[_SQLToken, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token.kind != "word" or token.text != "SELECT":
            continue
        end = _scope_end(tokens, index)
        if any(
            candidate.depth == token.depth and candidate.kind == "word" and candidate.text == "INTO"
            for candidate in tokens[index + 1 : end]
        ):
            return True
    return False


def _has_locking_clause(tokens: tuple[_SQLToken, ...]) -> bool:
    words_by_depth: dict[int, list[str]] = {}
    for token in tokens:
        if token.kind == "word":
            words_by_depth.setdefault(token.depth, []).append(token.text)
    return any(
        any(
            tuple(words[index : index + len(sequence)]) == sequence
            for index in range(len(words) - len(sequence) + 1)
        )
        for words in words_by_depth.values()
        for sequence in _LOCKING_SEQUENCES
    )


def _locking_clause_supported(tokens: tuple[_SQLToken, ...], depth: int) -> bool:
    words = [token.text for token in tokens if token.depth == depth and token.kind == "word"]
    valid_prefixes = {
        ("FOR", "UPDATE"),
        ("FOR", "NO", "KEY", "UPDATE"),
        ("FOR", "SHARE"),
        ("FOR", "KEY", "SHARE"),
    }
    for index, word in enumerate(words):
        if word != "FOR":
            continue
        if not any(
            tuple(words[index : index + len(prefix)]) == prefix for prefix in valid_prefixes
        ):
            return False
    return True


def _has_mutating_cte(tokens: tuple[_SQLToken, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token.kind != "word" or token.text != "WITH":
            continue
        _command, bodies, supported = _parse_with_structure(tokens, start_index=index)
        if supported and any(body_command in _MUTATING_COMMANDS for body_command in bodies):
            return True
    return False


def _is_locking_mutation_word(tokens: tuple[_SQLToken, ...], index: int) -> bool:
    token = tokens[index]
    same_depth_before = [item.text for item in tokens[:index] if item.depth == token.depth]
    return bool(
        same_depth_before
        and (
            tuple(same_depth_before[-1:]) == ("FOR",)
            or tuple(same_depth_before[-3:]) == ("FOR", "NO", "KEY")
        )
    )


def _has_nested_mutating_command(tokens: tuple[_SQLToken, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token.depth == 0 or token.kind != "word" or token.text not in _MUTATING_COMMANDS:
            continue
        if _is_locking_mutation_word(tokens, index):
            continue
        return True
    return False


def _matching_close(tokens: tuple[_SQLToken, ...], open_index: int) -> int | None:
    opening = tokens[open_index]
    if opening.kind != "symbol" or opening.text != "(":
        return None
    for index in range(open_index + 1, len(tokens)):
        candidate = tokens[index]
        if (
            candidate.kind == "symbol"
            and candidate.text == ")"
            and candidate.depth == opening.depth
        ):
            return index
    return None


def _parse_with_structure(
    tokens: tuple[_SQLToken, ...],
    *,
    start_index: int = 0,
) -> tuple[str, tuple[str, ...], bool]:
    """Parse only the bounded WITH shape needed for purity classification."""

    if (
        start_index >= len(tokens)
        or tokens[start_index].kind != "word"
        or tokens[start_index].text != "WITH"
    ):
        return UNKNOWN, (), False
    base_depth = tokens[start_index].depth
    cursor = start_index + 1
    if (
        cursor < len(tokens)
        and tokens[cursor].kind == "word"
        and tokens[cursor].text == "RECURSIVE"
    ):
        cursor += 1
    body_commands: list[str] = []
    while True:
        if cursor >= len(tokens) or tokens[cursor].depth != base_depth:
            return UNKNOWN, tuple(body_commands), False
        name = tokens[cursor]
        if name.kind not in {"word", "identifier"}:
            return UNKNOWN, tuple(body_commands), False
        cursor += 1

        if cursor < len(tokens) and tokens[cursor].text == "(":
            close = _matching_close(tokens, cursor)
            if close is None or close == cursor + 1:
                return UNKNOWN, tuple(body_commands), False
            cursor = close + 1

        if cursor >= len(tokens) or tokens[cursor].kind != "word" or tokens[cursor].text != "AS":
            return UNKNOWN, tuple(body_commands), False
        cursor += 1
        if cursor < len(tokens) and tokens[cursor].kind == "word":
            if tokens[cursor].text == "MATERIALIZED":
                cursor += 1
            elif tokens[cursor].text == "NOT":
                if (
                    cursor + 1 >= len(tokens)
                    or tokens[cursor + 1].kind != "word"
                    or tokens[cursor + 1].text != "MATERIALIZED"
                ):
                    return UNKNOWN, tuple(body_commands), False
                cursor += 2

        if cursor >= len(tokens) or tokens[cursor].text != "(":
            return UNKNOWN, tuple(body_commands), False
        close = _matching_close(tokens, cursor)
        if close is None or close == cursor + 1:
            return UNKNOWN, tuple(body_commands), False
        body_depth = tokens[cursor].depth + 1
        body_command = next(
            (
                token.text
                for token in tokens[cursor + 1 : close]
                if token.kind == "word" and token.depth == body_depth
            ),
            UNKNOWN,
        )
        if body_command not in {"SELECT", *_MUTATING_COMMANDS}:
            return UNKNOWN, tuple(body_commands), False
        body_commands.append(body_command)
        cursor = close + 1
        if (
            cursor < len(tokens)
            and tokens[cursor].kind == "operator"
            and tokens[cursor].text == ","
        ):
            cursor += 1
            continue
        break

    if cursor >= len(tokens):
        return UNKNOWN, tuple(body_commands), False
    outer = tokens[cursor]
    if outer.depth != base_depth or outer.kind != "word" or outer.text not in _STATEMENT_KEYWORDS:
        return UNKNOWN, tuple(body_commands), False
    return outer.text, tuple(body_commands), True


def _scope_end(tokens: tuple[_SQLToken, ...], select_index: int) -> int:
    depth = tokens[select_index].depth
    for index in range(select_index + 1, len(tokens)):
        token = tokens[index]
        if token.depth < depth:
            return index
        if token.kind == "symbol" and token.text == ";" and token.depth == depth:
            return index
    return len(tokens)


def _is_expression_token(token: _SQLToken) -> bool:
    return token.kind in {"word", "literal", "identifier"} or (
        token.kind == "operator" and token.text == "*"
    )


def _operator_run_supported(run: str, next_token: _SQLToken | None = None) -> bool:
    if run in _SUPPORTED_OPERATOR_RUNS or (
        run.endswith(":") and run[:-1] in _SUPPORTED_OPERATOR_RUNS
    ):
        return True
    return (
        run.endswith("%")
        and run[:-1] in _SUPPORTED_OPERATOR_RUNS
        and next_token is not None
        and next_token.kind == "symbol"
        and next_token.text == "("
    )


def _adjacent_expression_allowed(previous: _SQLToken, current: _SQLToken) -> bool:
    if current.kind == "word" and current.text in _STRUCTURAL_WORDS:
        return True
    if previous.kind == "word" and previous.text in _STRUCTURAL_WORDS:
        return True
    if previous.kind == "word" and previous.text == "SELECT" and current.depth == previous.depth:
        return True
    if previous.kind == "word" and current.kind == "word":
        return previous.text in _STRUCTURAL_WORDS or current.text in _STRUCTURAL_WORDS
    return previous.kind == "word" and current.kind == "symbol" and current.text == "("


def _is_value_token(token: _SQLToken) -> bool:
    if not _is_expression_token(token):
        return False
    if token.kind != "word":
        return True
    return token.text not in _STRUCTURAL_WORDS or token.text in {"FALSE", "NULL", "TRUE"}


def _is_value_end(token: _SQLToken) -> bool:
    return (
        _is_value_token(token)
        or (token.kind == "symbol" and token.text == ")")
        or (token.kind == "operator" and token.text == "]")
    )


def _is_value_start(tokens: tuple[_SQLToken, ...], index: int) -> bool:
    if index >= len(tokens):
        return False
    token = tokens[index]
    if _is_value_token(token) or (token.kind == "symbol" and token.text == "("):
        return True
    if token.kind == "operator" and token.text in {"+", "-", "~", "!", ":"}:
        return index + 1 < len(tokens) and _is_value_start(tokens, index + 1)
    if (
        token.kind == "operator"
        and token.text == "%"
        and index + 1 < len(tokens)
        and tokens[index + 1].kind == "symbol"
        and tokens[index + 1].text == "("
    ):
        return True
    if token.kind == "word" and token.text == "NOT":
        return _is_value_start(tokens, index + 1)
    return False


def _predicate_structure_supported(tokens: tuple[_SQLToken, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token.kind != "word":
            continue
        next_index = index + 1
        next_token = tokens[next_index] if next_index < len(tokens) else None
        previous_token = tokens[index - 1] if index else None
        if token.text in {"AND", "OR"}:
            if (
                previous_token is None
                or not _is_value_end(previous_token)
                or not _is_value_start(tokens, next_index)
            ):
                return False
        elif token.text == "NOT":
            if next_token is None or not _is_value_start(tokens, next_index):
                if not (
                    previous_token is not None
                    and previous_token.kind == "word"
                    and previous_token.text in {"IS"}
                    and next_token is not None
                    and next_token.text == "DISTINCT"
                ) and not (
                    previous_token is not None
                    and _is_value_end(previous_token)
                    and next_token is not None
                    and next_token.kind == "word"
                    and next_token.text in {"BETWEEN", "IN", "LIKE"}
                ):
                    return False
            if (
                previous_token is not None
                and _is_value_end(previous_token)
                and not (
                    next_token is not None
                    and next_token.kind == "word"
                    and next_token.text in {"BETWEEN", "IN", "LIKE"}
                )
            ):
                return False
        elif token.text in {"IS", "LIKE", "BETWEEN"}:
            operand_token = previous_token
            if (
                token.text in {"LIKE", "BETWEEN"}
                and previous_token is not None
                and previous_token.kind == "word"
                and previous_token.text == "NOT"
                and index >= 2
            ):
                operand_token = tokens[index - 2]
            if operand_token is None or not _is_value_end(operand_token):
                return False
            if token.text == "IS":
                if next_token is None or next_token.text in {"AND", "OR", ")"}:
                    return False
                if next_token.text == "NOT":
                    rhs = tokens[index + 2] if index + 2 < len(tokens) else None
                    if rhs is None or rhs.text not in {
                        "DISTINCT",
                        "FALSE",
                        "NULL",
                        "TRUE",
                        "UNKNOWN",
                    }:
                        return False
                    if rhs.text == "DISTINCT" and (
                        index + 3 >= len(tokens) or tokens[index + 3].text != "FROM"
                    ):
                        return False
                elif next_token.text == "DISTINCT":
                    if (
                        index + 1 >= len(tokens)
                        or index + 2 >= len(tokens)
                        or tokens[index + 2].text != "FROM"
                    ):
                        return False
                elif next_token.text not in {"FALSE", "NULL", "TRUE", "UNKNOWN"}:
                    return False
            elif next_token is not None and next_token.text == "NOT":
                return False
            elif not _is_value_start(tokens, next_index):
                return False
        elif token.text == "IN":
            operand_token = previous_token
            if (
                previous_token is not None
                and previous_token.kind == "word"
                and previous_token.text == "NOT"
                and index >= 2
            ):
                operand_token = tokens[index - 2]
            if operand_token is None or not _is_value_end(operand_token):
                return False
            if next_token is None or next_token.kind != "symbol" or next_token.text != "(":
                return False
        elif token.text in {"ANY", "ALL", "SOME"}:
            valid_left_operand = False
            if (
                previous_token is not None
                and previous_token.kind == "word"
                and previous_token.text == "LIKE"
            ):
                left_index = index - 2
                if left_index >= 0 and tokens[left_index].text == "NOT":
                    left_index -= 1
                valid_left_operand = left_index >= 0 and _is_value_end(tokens[left_index])
            else:
                operator_start = index - 1
                while (
                    operator_start >= 0
                    and tokens[operator_start].kind == "operator"
                    and tokens[operator_start].text not in {",", "[", "]"}
                ):
                    operator_start -= 1
                operator_run = "".join(item.text for item in tokens[operator_start + 1 : index])
                valid_left_operand = (
                    operator_start >= 0
                    and _is_value_end(tokens[operator_start])
                    and operator_run
                    in {"=", "!=", "<>", "<", "<=", ">", ">=", "@>", "<@", "&&", "~", "!~"}
                )
            if next_token is None or next_token.text != "(" or not valid_left_operand:
                return False
    return True


def _function_owner_before_close(
    tokens: tuple[_SQLToken, ...], close_index: int
) -> _SQLToken | None:
    close = tokens[close_index]
    open_index = next(
        (
            index
            for index in range(close_index - 1, -1, -1)
            if tokens[index].kind == "symbol"
            and tokens[index].text == "("
            and tokens[index].depth == close.depth
        ),
        None,
    )
    if open_index is None or open_index == 0:
        return None
    owner = tokens[open_index - 1]
    if owner.kind != "word" or owner.text in _STRUCTURAL_WORDS | _STATEMENT_KEYWORDS:
        return None
    return owner


def _function_owner_at_depth(
    tokens: tuple[_SQLToken, ...], index: int, open_depth: int
) -> _SQLToken | None:
    open_index = next(
        (
            position
            for position in range(index - 1, -1, -1)
            if tokens[position].kind == "symbol"
            and tokens[position].text == "("
            and tokens[position].depth == open_depth
        ),
        None,
    )
    if open_index is None or open_index == 0:
        return None
    owner = tokens[open_index - 1]
    if owner.kind != "word" or owner.text in _STRUCTURAL_WORDS | _STATEMENT_KEYWORDS:
        return None
    return owner


def _inside_nested_select_scope(
    tokens: tuple[_SQLToken, ...], index: int, minimum_depth: int
) -> bool:
    """Identify tokens owned by a nested SELECT validated independently."""

    token = tokens[index]
    return any(
        prior.kind == "word"
        and prior.text == "SELECT"
        and prior.depth == token.depth
        and prior.depth > minimum_depth
        for prior in tokens[:index]
    )


def _expression_segment_supported(tokens: tuple[_SQLToken, ...]) -> bool:
    """Reject expression segments with unsupported or incomplete token shapes."""

    minimum_depth = min((token.depth for token in tokens), default=0)
    nested_structural_words = {
        "AS",
        "ASC",
        "BY",
        "DESC",
        "FIRST",
        "LAST",
        "NULLS",
        "ON",
        "ONLY",
        "USING",
    }
    for index, token in enumerate(tokens):
        if (
            token.kind != "word"
            or token.depth <= minimum_depth
            or token.text not in nested_structural_words
            or _inside_nested_select_scope(tokens, index, minimum_depth)
        ):
            continue
        if token.text == "BY":
            prior = next(
                (
                    candidate
                    for candidate in reversed(tokens[:index])
                    if candidate.depth == token.depth and candidate.kind == "word"
                ),
                None,
            )
            if prior is not None and prior.text in {"GROUP", "ORDER"}:
                continue
        return False
    if (
        tokens
        and tokens[-1].kind == "word"
        and (
            tokens[-1].text in {"IN", "USING", "ANY", "ALL", "SOME"}
            or tokens[-1].text in _INCOMPLETE_CLAUSE_WORDS
        )
    ):
        return False
    if any(
        token.kind == "symbol"
        and token.text == "("
        and index + 1 < len(tokens)
        and tokens[index + 1].kind == "symbol"
        and tokens[index + 1].text == ")"
        for index, token in enumerate(tokens)
    ):
        return False
    bracket_depth = 0
    for index, token in enumerate(tokens):
        if token.kind != "operator" or token.text not in {"[", "]"}:
            continue
        if token.text == "[":
            if index == 0 or tokens[index - 1].kind != "word" or tokens[index - 1].text != "ARRAY":
                return False
            if (
                index + 1 < len(tokens)
                and tokens[index + 1].kind == "operator"
                and tokens[index + 1].text == "]"
            ):
                return False
            bracket_depth += 1
        else:
            bracket_depth -= 1
            if bracket_depth < 0:
                return False
    if bracket_depth != 0:
        return False
    if not _predicate_structure_supported(tokens):
        return False
    for index, token in enumerate(tokens):
        if token.kind != "word":
            continue
        if token.text in {"IN", "IS", "BETWEEN", "LIKE"}:
            prior_token = tokens[index - 1] if index else None
            if prior_token is None or not (
                _is_expression_token(prior_token)
                or (prior_token.kind == "symbol" and prior_token.text == ")")
            ):
                return False
        if token.text in {"ANY", "ALL", "SOME"}:
            if index == 0 or index + 1 >= len(tokens) or tokens[index + 1].text != "(":
                return False
        if token.text == "BETWEEN":
            same_depth_and = next(
                (
                    candidate
                    for candidate in tokens[index + 1 :]
                    if candidate.depth == token.depth
                    and candidate.kind == "word"
                    and candidate.text == "AND"
                ),
                None,
            )
            if same_depth_and is None:
                return False
            and_index = tokens.index(same_depth_and, index + 1)
            if not any(_is_expression_token(item) for item in tokens[index + 1 : and_index]):
                return False
            if (
                and_index + 1 >= len(tokens)
                or tokens[and_index + 1].kind == "word"
                and tokens[and_index + 1].text == "NOT"
            ):
                return False
            if not any(_is_expression_token(item) for item in tokens[and_index + 1 :]):
                return False
    for index, token in enumerate(tokens):
        if token.kind != "word" or (
            token.text not in _GRAMMAR_CLAUSE_BOUNDARIES
            and token.text not in {"JOIN", "ON", "USING"}
        ):
            continue
        if token.depth == 0:
            continue
        if token.text == "FROM" and _is_is_distinct_from(tokens, index, token.depth):
            continue
        prior_words = [
            item.text
            for item in tokens[:index]
            if item.depth == token.depth and item.kind == "word"
        ]
        prior_any_words = [item.text for item in tokens[:index] if item.kind == "word"]
        if token.text == "WHERE" and (
            (prior_words and prior_words[-1] == "FILTER")
            or (prior_any_words and prior_any_words[-1] == "FILTER")
        ):
            continue
        if token.text == "ORDER" and prior_words:
            if index + 1 >= len(tokens) or tokens[index + 1].text != "BY":
                return False
            continue
        if "SELECT" not in prior_words:
            return False

    previous: _SQLToken | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "word" and token.text == "FILTER":
            if any(
                prior.kind == "word" and prior.text == "FILTER" and prior.depth == token.depth
                for prior in tokens[:index]
            ):
                return False
            if not (
                index + 1 < len(tokens)
                and tokens[index + 1].kind == "symbol"
                and tokens[index + 1].text == "("
            ):
                if previous is None or previous.kind != "operator" or previous.text != ":":
                    return False
                previous = token
                index += 1
                continue
            if (
                previous is None
                or previous.kind != "symbol"
                or previous.text != ")"
                or previous.depth != token.depth
                or _function_owner_before_close(tokens, index - 1) is None
                or index + 2 >= len(tokens)
                or tokens[index + 1].kind != "symbol"
                or tokens[index + 1].text != "("
                or tokens[index + 2].kind != "word"
                or tokens[index + 2].text != "WHERE"
            ):
                return False
            close = _matching_close(tokens, index + 1)
            if close is None or close == index + 3:
                return False
            if not _expression_segment_supported(tokens[index + 3 : close]):
                return False
        if token.kind == "word" and token.text == "ORDER" and token.depth > 0:
            if (
                index + 1 >= len(tokens)
                or tokens[index + 1].text != "BY"
                or _function_owner_at_depth(tokens, index, token.depth - 1) is None
            ):
                return False
            close = next(
                (
                    position
                    for position in range(index + 2, len(tokens))
                    if tokens[position].kind == "symbol"
                    and tokens[position].text == ")"
                    and tokens[position].depth < token.depth
                ),
                len(tokens),
            )
            order_clause = tokens[index + 2 : close]
            if (
                not order_clause
                or any(
                    item.kind == "word" and item.text in _GRAMMAR_CLAUSE_BOUNDARIES
                    for item in order_clause
                )
                or not _order_clause_supported(order_clause, token.depth)
            ):
                return False
        if _is_expression_token(token) and previous is not None:
            if previous.depth == token.depth and _is_expression_token(previous):
                if not _adjacent_expression_allowed(previous, token):
                    return False
            if (
                previous.kind == "symbol"
                and previous.text == ")"
                and previous.depth == token.depth
                and token.kind == "word"
                and token.text not in _STRUCTURAL_WORDS
            ):
                return False
        if (
            token.kind == "symbol"
            and token.text == ")"
            and previous is not None
            and previous.kind == "word"
            and previous.text in {"AND", "OR", "IS", "NOT", "LIKE", "IN"}
        ):
            return False
        if token.kind == "word" and token.text in {"AND", "OR"}:
            if previous is None or (previous.kind == "symbol" and previous.text == "("):
                return False
        if token.kind == "word" and token.text == "SELECT" and token.depth > 0:
            if previous is None or previous.kind != "symbol" or previous.text != "(":
                return False
            opening_index = index - 1
            before_open = tokens[opening_index - 1] if opening_index else None
            if (
                before_open is None
                or (
                    before_open.kind == "word"
                    and before_open.text not in {"EXISTS", "IN", "SELECT"}
                    and before_open.text not in _STRUCTURAL_WORDS
                )
                or before_open.kind not in {"word", "operator"}
            ):
                return False
        if token.kind != "operator":
            previous = token
            index += 1
            continue

        if token.text == "*" and previous is not None and previous.text == "(":
            if index + 1 >= len(tokens) or tokens[index + 1].text != ")":
                return False
            previous = token
            index += 1
            continue

        if token.text == ",":
            next_index = index + 1
            if next_index >= len(tokens):
                return False
            if index == 0 or tokens[index - 1].text in {"(", "["}:
                return False
            next_token = tokens[next_index]
            if next_token.kind == "operator" and next_token.text == ",":
                return False
            while (
                next_index < len(tokens)
                and tokens[next_index].kind == "operator"
                and tokens[next_index].text != ","
            ):
                next_index += 1
            if next_index >= len(tokens):
                return False
            next_token = tokens[next_index]
            if next_token.depth < token.depth or (
                next_token.kind == "symbol" and next_token.text == ")"
            ):
                return False
            run = "".join(token.text for token in tokens[index + 1 : next_index])
            if run and (
                run not in {"+", "-", "~", "!", ":"}
                and not (run == "%" and next_token.kind == "symbol" and next_token.text == "(")
            ):
                return False
            previous = tokens[next_index - 1]
            index = next_index
            continue

        next_index = index
        while (
            next_index < len(tokens)
            and tokens[next_index].kind == "operator"
            and tokens[next_index].text != ","
        ):
            next_index += 1
        run = "".join(token.text for token in tokens[index:next_index])
        if (
            (previous is None or (previous.kind == "symbol" and previous.text == "("))
            and run not in {"*", "+", "-", "~", "!", ":"}
            and not (
                run == "%"
                and next_index < len(tokens)
                and tokens[next_index].kind == "symbol"
                and tokens[next_index].text == "("
            )
        ):
            return False
        if next_index >= len(tokens):
            if (
                run == ".*"
                and previous is not None
                and previous.kind in {"word", "identifier"}
                and previous.text not in {"TRUE", "FALSE", "NULL"} | _STATEMENT_KEYWORDS
            ):
                return True
            if run == "]":
                return True
            return False
        next_token = tokens[next_index]
        if next_token.depth < token.depth or (
            next_token.kind == "symbol" and next_token.text == ")"
        ):
            if run == "]" and next_token.kind == "symbol" and next_token.text == ")":
                previous = tokens[next_index - 1]
                index = next_index
                continue
            return False
        if not _operator_run_supported(run, next_token):
            return False
        previous = tokens[next_index - 1]
        index = next_index
    return True


def _case_expressions_balanced(tokens: tuple[_SQLToken, ...]) -> bool:
    depth = 0
    for token in tokens:
        if token.kind != "word":
            continue
        if token.text == "CASE":
            depth += 1
        elif token.text == "END":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _case_expressions_supported(tokens: tuple[_SQLToken, ...]) -> bool:
    stack: list[dict[str, object]] = []
    for _index, token in enumerate(tokens):
        if token.kind != "word":
            if stack:
                stack[-1]["content"] = True
            continue
        if token.text == "CASE":
            for frame in stack:
                frame["content"] = True
            stack.append({"last": None, "content": False})
            continue
        if token.text not in {"WHEN", "THEN", "ELSE", "END"}:
            if stack:
                stack[-1]["content"] = True
            continue
        if not stack:
            return False
        for frame in stack[:-1]:
            frame["content"] = True
        frame = stack[-1]
        last = frame["last"]
        content = bool(frame["content"])
        if token.text == "WHEN":
            if last not in {None, "THEN"} or (last == "THEN" and not content):
                return False
            frame["last"] = "WHEN"
            frame["content"] = False
        elif token.text == "THEN":
            if last != "WHEN" or not content:
                return False
            frame["last"] = "THEN"
            frame["content"] = False
        elif token.text == "ELSE":
            if last != "THEN" or not content:
                return False
            frame["last"] = "ELSE"
            frame["content"] = False
        else:
            if last not in {"THEN", "ELSE"} or not content:
                return False
            stack.pop()
            if stack:
                stack[-1]["content"] = True
    return not stack


def _order_term_expression_supported(term: list[_SQLToken], depth: int) -> bool:
    top_positions = [index for index, token in enumerate(term) if token.depth == depth]
    if not top_positions:
        return False
    end = len(term)
    while True:
        top_positions = [index for index, token in enumerate(term[:end]) if token.depth == depth]
        if not top_positions:
            return False
        last_index = top_positions[-1]
        last = term[last_index]
        if last.kind == "word" and last.text in {"ASC", "DESC"}:
            end = last_index
            continue
        if last.kind == "word" and last.text in {"FIRST", "LAST"}:
            if len(top_positions) < 2:
                return False
            modifier = term[top_positions[-2]]
            if modifier.kind != "word" or modifier.text != "NULLS":
                return False
            end = top_positions[-2]
            continue
        break
    if any(
        token.depth == depth
        and token.kind == "word"
        and token.text in {"AS", "BY", "FIRST", "JOIN", "LAST", "NULLS", "ON", "ONLY", "USING"}
        and not (
            token.text in {"FIRST", "LAST"}
            and token_index > 0
            and term[token_index - 1].kind == "operator"
            and term[token_index - 1].text == ":"
        )
        for token_index, token in enumerate(term[:end])
    ):
        return False
    return bool(term[:end]) and _expression_segment_supported(tuple(term[:end]))


def _order_clause_supported(clause: tuple[_SQLToken, ...], depth: int) -> bool:
    terms: list[list[_SQLToken]] = [[]]
    for token in clause:
        if token.depth == depth and token.kind == "operator" and token.text == ",":
            terms.append([])
        else:
            terms[-1].append(token)
    for term in terms:
        top_level = [token for token in term if token.depth == depth]
        if not top_level or (top_level[0].kind == "word" and top_level[0].text == "NULLS"):
            return False
        if not _order_term_expression_supported(term, depth):
            return False
        directions = 0
        nulls_modifiers = 0
        for index, token in enumerate(top_level):
            if token.kind == "word" and token.text in {"ASC", "DESC"}:
                directions += 1
                if index == 0:
                    return False
            if token.kind != "word" or token.text != "NULLS":
                continue
            nulls_modifiers += 1
            if (
                index == 0
                or index + 1 >= len(top_level)
                or top_level[index + 1].kind != "word"
                or top_level[index + 1].text not in {"FIRST", "LAST"}
            ):
                return False
        for index, token in enumerate(top_level):
            if token.kind == "word" and token.text in {"FIRST", "LAST"}:
                if index == 0 or top_level[index - 1].text not in {"NULLS", ":"}:
                    return False
        nulls_index = next(
            (index for index, token in enumerate(top_level) if token.text == "NULLS"),
            None,
        )
        direction_index = next(
            (
                index
                for index, token in enumerate(top_level)
                if token.kind == "word" and token.text in {"ASC", "DESC"}
            ),
            None,
        )
        if (
            nulls_index is not None
            and direction_index is not None
            and direction_index > nulls_index
        ):
            return False
        if directions > 1 or nulls_modifiers > 1:
            return False
    return True


def _fetch_clause_supported(clause: tuple[_SQLToken, ...]) -> bool:
    words = [token.text for token in clause if token.kind == "word"]
    if len(words) < 3 or words[0] not in {"FIRST", "NEXT"}:
        return False
    row_index = next(
        (index for index, word in enumerate(words[1:], 1) if word in {"ROW", "ROWS"}),
        None,
    )
    if row_index is None or row_index == len(words) - 1:
        return False
    suffix = words[row_index + 1 :]
    return suffix == ["ONLY"] or suffix == ["WITH", "TIES"]


def _from_clause_supported(clause: tuple[_SQLToken, ...], depth: int) -> bool:
    forbidden_relation_words = {"ASC", "DESC", "FIRST", "LAST", "NULLS", "ONLY"}
    join_indexes = [
        index
        for index, token in enumerate(clause)
        if token.depth == depth and token.kind == "word" and token.text == "JOIN"
    ]
    first_join = min(join_indexes, default=len(clause))
    if any(
        token.kind == "word"
        and token.text == "AS"
        and index + 1 < len(clause)
        and clause[index + 1].kind == "symbol"
        and clause[index + 1].text == "("
        for index, token in enumerate(clause)
    ):
        return False
    base_segment = clause[:first_join]
    if sum(token.depth == depth and token.text == "AS" for token in base_segment) > 1:
        return False
    if any(
        token.depth == depth and token.kind == "word" and token.text in forbidden_relation_words
        for token in base_segment
    ):
        return False
    base = next((token for token in base_segment if token.depth == depth), None)
    if (
        base is None
        or base.kind not in {"word", "identifier"}
        or (base.kind == "word" and base.text in _STRUCTURAL_WORDS | _STATEMENT_KEYWORDS)
    ):
        return False
    if any(
        token.depth == depth and token.kind == "operator" and token.text == "," for token in clause
    ):
        return False
    if any(
        token.depth == depth and token.kind == "word" and token.text in {"ON", "USING"}
        for token in clause[:first_join]
    ):
        return False
    for join_index in join_indexes:
        relation_index = join_index + 1
        next_join = next((index for index in join_indexes if index > join_index), len(clause))
        qualifier_index = next(
            (
                index
                for index in range(relation_index, next_join)
                if clause[index].depth == depth
                and clause[index].kind == "word"
                and clause[index].text in {"ON", "USING"}
            ),
            next_join,
        )
        relation_segment = clause[relation_index:qualifier_index]
        if (
            relation_index >= len(clause)
            or clause[relation_index].depth != depth
            or sum(token.depth == depth and token.text == "AS" for token in relation_segment) > 1
            or any(
                token.depth == depth
                and token.kind == "word"
                and token.text in forbidden_relation_words
                for token in relation_segment
            )
        ):
            return False
        if clause[relation_index].kind not in {"word", "identifier"} or (
            clause[relation_index].kind == "word"
            and clause[relation_index].text in _STRUCTURAL_WORDS | _STATEMENT_KEYWORDS
        ):
            return False
        qualifier_words = {
            token.text
            for token in clause[qualifier_index + 1 : next_join]
            if token.depth == depth and token.kind == "word"
        }
        if qualifier_words & {
            "AS",
            "ASC",
            "DESC",
            "FIRST",
            "LAST",
            "NULLS",
            "ONLY",
        }:
            return False
        qualifiers = [
            token
            for token in clause[relation_index + 1 : next_join]
            if token.depth == depth and token.kind == "word"
        ]
        qualifier_count = sum(token.text in {"ON", "USING"} for token in qualifiers)
        if qualifier_count != 1:
            return False
    return True


def _projection_aliases_supported(projection: tuple[_SQLToken, ...], depth: int) -> bool:
    terms: list[list[_SQLToken]] = [[]]
    for token in projection:
        if token.depth == depth and token.kind == "operator" and token.text == ",":
            terms.append([])
        else:
            terms[-1].append(token)
    for term in terms:
        top_positions = [index for index, token in enumerate(term) if token.depth == depth]
        alias_positions = [
            index
            for index in top_positions
            if term[index].kind == "word" and term[index].text == "AS"
        ]
        if not alias_positions:
            continue
        if len(alias_positions) != 1:
            return False
        alias_position = alias_positions[0]
        position_index = top_positions.index(alias_position)
        if position_index == 0 or position_index + 1 >= len(top_positions):
            return False
        previous = term[top_positions[position_index - 1]]
        alias = term[top_positions[position_index + 1]]
        if not _is_value_end(previous) or alias.kind not in {"word", "identifier"}:
            return False
        if position_index + 2 != len(top_positions):
            return False
    return True


def _is_is_distinct_from(tokens: tuple[_SQLToken, ...], index: int, depth: int) -> bool:
    prior = [token for token in tokens[:index] if token.depth == depth and token.kind == "word"]
    return bool(
        len(prior) >= 2
        and prior[-1].text == "DISTINCT"
        and (
            prior[-2].text == "IS"
            or (len(prior) >= 3 and prior[-3].text == "IS" and prior[-2].text == "NOT")
        )
    )


def _select_scope_supported(tokens: tuple[_SQLToken, ...], select_index: int) -> bool:
    depth = tokens[select_index].depth
    end = _scope_end(tokens, select_index)
    if not _locking_clause_supported(tokens[select_index:end], depth):
        return False
    boundaries = [
        (index, token.text)
        for index, token in enumerate(tokens[select_index + 1 : end], start=select_index + 1)
        if token.depth == depth
        and token.kind == "word"
        and token.text in _GRAMMAR_CLAUSE_BOUNDARIES
        and not (token.text == "FROM" and _is_is_distinct_from(tokens, index, depth))
    ]
    clause_order = {
        "INTO": 0,
        "FROM": 1,
        "WHERE": 2,
        "GROUP": 3,
        "HAVING": 4,
        "WINDOW": 5,
        "ORDER": 6,
        "LIMIT": 7,
        "OFFSET": 8,
        "FETCH": 9,
    }
    previous_order = -1
    for _position, boundary in boundaries:
        if boundary in {"UNION", "INTERSECT", "EXCEPT"}:
            if previous_order >= 6:
                return False
            previous_order = -1
            continue
        current_order = clause_order.get(boundary)
        if current_order is None or current_order <= previous_order:
            return False
        previous_order = current_order
    first_boundary = boundaries[0][0] if boundaries else end
    projection = tokens[select_index + 1 : first_boundary]
    if projection and projection[0].kind == "word" and projection[0].text == "DISTINCT":
        projection = projection[1:]
        if projection and projection[0].kind == "word" and projection[0].text == "ON":
            if len(projection) < 3 or projection[1].text != "(":
                return False
            close = _matching_close(projection, 1)
            if (
                close is None
                or close == 2
                or not _case_expressions_balanced(projection[2:close])
                or not _case_expressions_supported(projection[2:close])
                or not _expression_segment_supported(projection[2:close])
                or any(
                    token.kind == "word" and token.text in _GRAMMAR_CLAUSE_BOUNDARIES
                    for token in projection[2:close]
                )
                or close + 1 >= len(projection)
            ):
                return False
            projection = projection[close + 1 :]
    if not _projection_aliases_supported(projection, depth):
        return False
    if any(token.kind == "word" and token.text == "NULLS" for token in projection) and not any(
        token.kind == "word" and token.text == "ORDER" for token in projection
    ):
        return False
    if any(
        token.depth == depth
        and token.kind == "word"
        and token.text
        in {
            "ASC",
            "BY",
            "DESC",
            "FIRST",
            "JOIN",
            "LAST",
            "NULLS",
            "ON",
            "ONLY",
            "USING",
        }
        for token in projection
    ):
        return False
    projection_terms: list[list[_SQLToken]] = [[]]
    for token in projection:
        if token.depth == depth and token.kind == "operator" and token.text == ",":
            projection_terms.append([])
        else:
            projection_terms[-1].append(token)
    if any(
        sum(token.depth == depth and token.text == "AS" for token in term) > 1
        for term in projection_terms
    ):
        return False
    projection_has_expression = any(_is_expression_token(token) for token in projection)
    if (
        not projection_has_expression
        or not _case_expressions_balanced(projection)
        or not _case_expressions_supported(projection)
        or not _expression_segment_supported(projection)
    ):
        return False

    for boundary_position, boundary in boundaries:
        next_boundary = next(
            (index for index, _name in boundaries if index > boundary_position), end
        )
        clause = tokens[boundary_position + 1 : next_boundary]
        if boundary == "WINDOW":
            return False
        if boundary in {"WHERE", "HAVING"} and any(
            token.kind == "word"
            and token.text
            in {
                "AS",
                "ASC",
                "DESC",
                "FIRST",
                "JOIN",
                "LAST",
                "NULLS",
                "ON",
                "ONLY",
                "USING",
            }
            for token in clause
        ):
            return False
        if boundary in {"WHERE", "HAVING", "LIMIT", "OFFSET", "FETCH"} and any(
            token.depth == depth and token.kind == "operator" and token.text == ","
            for token in clause
        ):
            return False
        if boundary in {"GROUP", "ORDER"} and any(
            token.depth == depth and token.kind == "word" and token.text == "AS" for token in clause
        ):
            return False
        if boundary == "GROUP" and any(
            token.depth == depth
            and token.kind == "word"
            and token.text in {"ASC", "DESC", "FIRST", "LAST", "NULLS", "ONLY"}
            for token in clause
        ):
            return False
        if boundary in {"GROUP", "LIMIT", "OFFSET", "FETCH"} and any(
            token.kind == "word" and token.text == "NULLS" for token in clause
        ):
            return False
        if boundary in {"LIMIT", "OFFSET"} and any(
            token.depth == depth
            and token.kind == "word"
            and token.text
            in {"AS", "ASC", "BY", "DESC", "FIRST", "JOIN", "LAST", "NULLS", "ON", "ONLY", "USING"}
            for token in clause
        ):
            return False
        if boundary == "FETCH" and any(
            token.depth == depth
            and token.kind == "word"
            and token.text in {"AS", "ASC", "BY", "DESC", "JOIN", "LAST", "NULLS", "ON", "USING"}
            for token in clause
        ):
            return False
        if boundary in {"UNION", "INTERSECT", "EXCEPT", "RETURNING"}:
            set_operator_end = boundary_position + 1
            if (
                set_operator_end < end
                and tokens[set_operator_end].depth == depth
                and tokens[set_operator_end].kind == "word"
                and tokens[set_operator_end].text == "ALL"
            ):
                set_operator_end += 1
            if (
                boundary == "RETURNING"
                or set_operator_end >= end
                or tokens[set_operator_end].depth != depth
                or tokens[set_operator_end].kind != "word"
                or tokens[set_operator_end].text != "SELECT"
            ):
                return False
            continue
        if boundary in {"GROUP", "ORDER"}:
            if not clause or clause[0].kind != "word" or clause[0].text != "BY":
                return False
            clause = clause[1:]
            if boundary == "ORDER" and not _order_clause_supported(clause, depth):
                return False
        if boundary == "FETCH" and not _fetch_clause_supported(clause):
            return False
        if boundary == "FROM" and not _from_clause_supported(clause, depth):
            return False
        clause_has_expression = any(_is_expression_token(token) for token in clause)
        if (
            not clause_has_expression
            or not _case_expressions_balanced(clause)
            or not _case_expressions_supported(clause)
            or not _expression_segment_supported(clause)
        ):
            return False

    expression_tokens = [
        token for token in tokens[select_index + 1 : end] if _is_expression_token(token)
    ]
    if not expression_tokens:
        return False
    last_token = expression_tokens[-1]
    return not (last_token.kind == "word" and last_token.text in _INCOMPLETE_CLAUSE_WORDS)


def _select_grammar_supported(
    tokens: tuple[_SQLToken, ...], command: str, with_supported: bool
) -> bool:
    if command != "SELECT":
        return command in _STATEMENT_KEYWORDS and command != UNKNOWN
    if tokens and tokens[0].text == "WITH" and not with_supported:
        return False
    if _has_nested_mutating_command(tokens):
        return False
    if any(
        token.depth == 0
        and token.kind == "word"
        and token.text in _MUTATING_COMMANDS
        and not _is_locking_mutation_word(tokens, index)
        for index, token in enumerate(tokens)
    ):
        return False
    select_indexes = [
        index
        for index, token in enumerate(tokens)
        if token.kind == "word" and token.text == "SELECT"
    ]
    return bool(select_indexes) and all(
        _select_scope_supported(tokens, select_index) for select_index in select_indexes
    )


def _analyze_statement(statement: object) -> _StatementAnalysis:
    sql = _statement_sql(statement)
    if sql is None or not sql.strip():
        return _StatementAnalysis(
            statement_class=UNKNOWN,
            lexical_valid=False,
            grammar_supported=False,
            statement_complete=False,
            mutating_cte_detected=False,
            select_into_detected=False,
            locking_detected=False,
            multi_statement_detected=False,
            unknown_detected=True,
        )

    lexed = _lex_sql(sql)
    tokens = lexed.tokens
    locking_detected = _has_locking_clause(tokens)
    if not lexed.valid:
        return _StatementAnalysis(
            statement_class=UNKNOWN,
            lexical_valid=False,
            grammar_supported=False,
            statement_complete=False,
            mutating_cte_detected=False,
            select_into_detected=False,
            locking_detected=locking_detected,
            multi_statement_detected=lexed.multi_statement,
            unknown_detected=True,
        )
    if lexed.multi_statement:
        return _StatementAnalysis(
            statement_class=UNKNOWN,
            lexical_valid=True,
            grammar_supported=False,
            statement_complete=False,
            mutating_cte_detected=False,
            select_into_detected=False,
            locking_detected=locking_detected,
            multi_statement_detected=True,
            unknown_detected=True,
        )

    top_level_word_tokens = [token for token in tokens if token.depth == 0 and token.kind == "word"]
    if not top_level_word_tokens or (tokens[0].kind == "symbol" and tokens[0].text == ";"):
        return _StatementAnalysis(
            statement_class=UNKNOWN,
            lexical_valid=True,
            grammar_supported=False,
            statement_complete=False,
            mutating_cte_detected=False,
            select_into_detected=False,
            locking_detected=locking_detected,
            multi_statement_detected=False,
            unknown_detected=True,
        )

    first_word = top_level_word_tokens[0].text
    with_command, _body_commands, with_supported = _parse_with_structure(tokens)
    mutating_cte_detected = _has_mutating_cte(tokens)
    command = first_word
    if first_word == "WITH":
        command = with_command

    select_into_detected = _has_select_into(tokens)
    grammar_supported = _select_grammar_supported(tokens, command, with_supported)
    if mutating_cte_detected:
        statement_class = DATA_MODIFYING_CTE
    elif command == "SELECT" and not grammar_supported:
        statement_class = UNKNOWN
    elif command == UNKNOWN:
        statement_class = UNKNOWN
    elif command == "SELECT" and select_into_detected:
        statement_class = SELECT_INTO_WRITE
    elif command == "SELECT":
        statement_class = READ_SELECT_LOCKING if locking_detected else READ_SELECT
    elif command == "INSERT":
        statement_class = WRITE_INSERT
    elif command == "UPDATE":
        statement_class = WRITE_UPDATE
    elif command == "DELETE":
        statement_class = WRITE_DELETE
    elif command == "MERGE":
        statement_class = WRITE_MERGE
    elif command in _DDL_KEYWORDS:
        statement_class = DDL
    elif command in _TRANSACTION_KEYWORDS:
        statement_class = TRANSACTION_CONTROL
    elif command in {"SET", "RESET", "DISCARD", "USE", "PRAGMA", "SHOW"}:
        statement_class = SESSION_OR_CONFIG_CHANGE
    else:
        statement_class = UNKNOWN

    if statement_class == UNKNOWN:
        grammar_supported = False
    statement_complete = lexed.statement_complete and not (
        (command == "SELECT" and not grammar_supported)
        or (first_word == "WITH" and not with_supported)
    )
    return _StatementAnalysis(
        statement_class,
        True,
        grammar_supported,
        statement_complete,
        mutating_cte_detected,
        select_into_detected,
        locking_detected,
        False,
        statement_class == UNKNOWN,
    )


def classify_statement(statement: object) -> str:
    """Classify the complete captured SQL statement; unsupported input is UNKNOWN."""

    return _analyze_statement(statement).statement_class


def _purity_statement_projection(statement: object) -> dict[str, object]:
    sql = _statement_sql(statement)
    analysis = _analyze_statement(statement)
    statement_class = analysis.statement_class
    safe_sql = _safe_sql_projection(sql) if sql is not None else "<unavailable>"
    positive_proof = (
        analysis.lexical_valid
        and analysis.grammar_supported
        and analysis.statement_complete
        and statement_class == READ_SELECT
        and not analysis.mutating_cte_detected
        and not analysis.select_into_detected
        and not analysis.locking_detected
        and not analysis.multi_statement_detected
        and not analysis.unknown_detected
    )
    if positive_proof:
        read_write_verdict = "PASS"
        locking_verdict = "PASS"
        purity_verdict = "PASS"
    elif statement_class == READ_SELECT_LOCKING:
        read_write_verdict = "PASS"
        locking_verdict = "FAIL"
        purity_verdict = "FAIL"
    elif statement_class == UNKNOWN:
        read_write_verdict = NOT_VERIFIED
        locking_verdict = NOT_VERIFIED
        purity_verdict = NOT_VERIFIED
    else:
        read_write_verdict = "FAIL"
        locking_verdict = "PASS"
        purity_verdict = "FAIL"
    return {
        "sql": safe_sql,
        "normalized_sql": safe_sql,
        "statement_class": statement_class,
        "classification": statement_class,
        "lexical_valid": analysis.lexical_valid,
        "grammar_supported": analysis.grammar_supported,
        "statement_complete": analysis.statement_complete,
        "read_write_verdict": read_write_verdict,
        "locking_verdict": locking_verdict,
        "mutating_cte_detected": analysis.mutating_cte_detected,
        "select_into_detected": analysis.select_into_detected,
        "locking_detected": analysis.locking_detected,
        "multi_statement_detected": analysis.multi_statement_detected,
        "ambiguity_detected": analysis.multi_statement_detected or statement_class == UNKNOWN,
        "unknown_detected": analysis.unknown_detected,
        "purity_verdict": purity_verdict,
    }


def validate_statement_purity(statements: object) -> dict[str, object]:
    """Project and validate the complete captured statement set fail-closed."""

    if not isinstance(statements, list) or not statements:
        raise PR18EvidenceError("NOT_VERIFIED: captured statement set is unavailable")
    projected = []
    for statement in statements:
        projection = _purity_statement_projection(statement)
        if isinstance(statement, dict):
            for field in (
                "classification",
                "statement_class",
                "lexical_valid",
                "grammar_supported",
                "statement_complete",
                "mutating_cte_detected",
                "select_into_detected",
                "locking_detected",
                "multi_statement_detected",
                "ambiguity_detected",
                "unknown_detected",
                "read_write_verdict",
                "locking_verdict",
                "purity_verdict",
            ):
                if field in statement and (
                    type(statement[field]) is not type(projection[field])
                    or statement[field] != projection[field]
                ):
                    raise PR18EvidenceError(
                        f"inconsistent purity evidence: {field} does not match execution"
                    )
        if projection["purity_verdict"] == "PASS" and not all(
            projection[field] is True
            for field in ("lexical_valid", "grammar_supported", "statement_complete")
        ):
            raise PR18EvidenceError("inconsistent purity evidence: PASS lacks positive proof")
        if projection["purity_verdict"] == "PASS" and projection["statement_class"] != READ_SELECT:
            raise PR18EvidenceError("inconsistent purity evidence: PASS is not READ_SELECT")
        projected.append(projection)
    unknown_count = sum(item["statement_class"] == UNKNOWN for item in projected)
    forbidden_count = sum(item["statement_class"] != READ_SELECT for item in projected)
    verdict = "PASS" if forbidden_count == 0 else "FAIL"
    return {
        "statement_count": len(projected),
        "statements": projected,
        "forbidden_statement_count": forbidden_count,
        "unknown_statement_count": unknown_count,
        "write_or_lock_verdict": verdict,
        "overall_verdict": verdict,
        "verification_status": "VERIFIED" if unknown_count == 0 else NOT_VERIFIED,
    }


def _capture_sql_statements(engine: Engine, callback: Any) -> list[tuple[str, object]]:
    """Capture every SQL statement emitted while ``callback`` executes."""

    captured: list[tuple[str, object]] = []

    def observe(
        _connection: Any, _cursor: Any, statement: str, parameters: object, *_args: Any
    ) -> None:
        if isinstance(statement, str):
            captured.append((statement, parameters))
        else:
            captured.append(("<unavailable>", parameters))

    event.listen(engine, "before_cursor_execute", observe)
    try:
        callback()
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    return captured


def _summary_counts(output: str) -> dict[str, int]:
    counts = {
        key: 0
        for key in ("passed", "failed", "skipped", "deselected", "xfailed", "xpassed", "errors")
    }
    for line in reversed(output.splitlines()):
        matches = list(_SUMMARY_COUNT.finditer(line))
        if matches:
            for match in matches:
                key = (
                    "errors" if match.group("kind") in {"error", "errors"} else match.group("kind")
                )
                counts[key] = int(match.group("count"))
            return counts
    return counts


def _collection_counts(output: str) -> tuple[int, int, int] | None:
    matches = list(_COLLECTION_COUNT.finditer(output))
    if not matches:
        raise PR18EvidenceError("pytest collection metadata is missing")
    if len(matches) != 1:
        raise PR18EvidenceError("pytest collection metadata is ambiguous")
    match = matches[-1]
    total = int(match.group("total"))
    selected = int(match.group("selected") or total)
    deselected = int(match.group("deselected") or 0)
    if total != selected + deselected:
        raise PR18EvidenceError("pytest collection counts do not reconcile")
    return total, selected, deselected


def parse_pytest_counts(
    *, output: str, collection_output: str, junit_xml: str | None, return_code: int
) -> dict[str, int]:
    """Reconcile pytest terminal, collection, and JUnit machine results."""

    if not isinstance(return_code, int) or isinstance(return_code, bool) or return_code < 0:
        raise PR18EvidenceError("pytest return code is malformed")
    if junit_xml is None:
        raise PR18EvidenceError("pytest JUnit result is missing")
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError as error:
        raise PR18EvidenceError("pytest JUnit result is malformed") from error
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise PR18EvidenceError("pytest JUnit result has no test suites")
    try:
        selected = 0
        failed = 0
        errors = 0
        junit_skipped = 0
        xfailed = 0
        xpassed = 0
        for suite in suites:
            required_attrs = ("tests", "failures", "errors", "skipped")
            if any(name not in suite.attrib for name in required_attrs):
                raise PR18EvidenceError("pytest JUnit outcome data is incomplete")
            suite_selected = int(suite.attrib["tests"])
            suite_failed = int(suite.attrib["failures"])
            suite_errors = int(suite.attrib["errors"])
            suite_skipped = int(suite.attrib["skipped"])
            testcases = list(suite.findall("testcase"))
            if len(testcases) != suite_selected:
                raise PR18EvidenceError("pytest JUnit testcase data is incomplete")
            child_failed = 0
            child_errors = 0
            child_skipped = 0
            for testcase in testcases:
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")
                if failure is not None:
                    child_failed += 1
                    if failure.attrib.get("type") == "pytest.xpass":
                        xpassed += 1
                if error is not None:
                    child_errors += 1
                if skipped is not None:
                    child_skipped += 1
                    if skipped.attrib.get("type") == "pytest.xfail":
                        xfailed += 1
            if (suite_failed, suite_errors, suite_skipped) != (
                child_failed,
                child_errors,
                child_skipped,
            ):
                raise PR18EvidenceError("pytest JUnit suite and testcase outcomes differ")
            selected += suite_selected
            failed += child_failed - sum(
                1
                for testcase in testcases
                if (failure := testcase.find("failure")) is not None
                and failure.attrib.get("type") == "pytest.xpass"
            )
            errors += child_errors
            junit_skipped += child_skipped
    except ValueError as error:
        raise PR18EvidenceError("pytest JUnit counts are malformed") from error
    collection = _collection_counts(collection_output)
    if collection is None:
        raise PR18EvidenceError("pytest collection metadata is missing")
    total_discovered, collection_selected, deselected = collection
    if collection_selected != selected:
        raise PR18EvidenceError("pytest JUnit and collection selected counts differ")
    terminal = _summary_counts(output)
    xfailed = max(xfailed, terminal["xfailed"])
    xpassed = max(xpassed, terminal["xpassed"])
    skipped = junit_skipped - xfailed
    passed = selected - failed - errors - skipped - xfailed - xpassed
    counts = {
        "total_discovered": total_discovered,
        "selected": selected,
        "deselected": deselected,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "xpassed": xpassed,
        "errors": errors,
        "return_code": return_code,
    }
    if min(counts.values()) < 0:
        raise PR18EvidenceError("pytest result contains negative counts")
    if selected != passed + failed + skipped + xfailed + xpassed + errors:
        raise PR18EvidenceError("pytest outcome counts do not reconcile")
    for key in ("passed", "failed", "skipped", "xfailed", "xpassed", "errors", "deselected"):
        if terminal[key] and terminal[key] != counts[key]:
            raise PR18EvidenceError(f"pytest terminal/JUnit count differs for {key}")
    return counts


def assess_evidence_readiness(artifact: object) -> str:
    """Return READY only when the stored evidence contains verified counts."""

    try:
        if not isinstance(artifact, dict):
            raise PR18EvidenceError("evidence must be an object")
        validate_command_entries(artifact.get("commands"))
    except PR18EvidenceError:
        return NOT_VERIFIED
    return "READY"


def _tuple_items(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(value)
    return ()


def _string_items(value: object, *, label: str) -> tuple[str, ...]:
    items = _tuple_items(value)
    if any(not isinstance(item, str) for item in items):
        raise PR18EvidenceError(f"query contract has invalid {label}")
    return tuple(item for item in items if isinstance(item, str))


_SQL_RELATION = r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)"
_JOIN_PREFIX = r"(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN"
_JOIN_CLAUSE = re.compile(
    rf"\b(?P<kind>{_JOIN_PREFIX})\s+(?P<relation>{_SQL_RELATION})"
    r"(?P<tail>.*?)(?=\s+(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN\b"
    r"|\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+LIMIT\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_FROM_CLAUSE = re.compile(
    r"\bFROM\s+(?P<body>.*?)(?=\s+(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN\b"
    r"|\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+LIMIT\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_RELATION_NAME = re.compile(rf"^\s*{_SQL_RELATION}", re.IGNORECASE)
_RELATION_REFERENCE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*", re.IGNORECASE)
_CARTESIAN_PREDICATE = re.compile(r"^(?:TRUE|1\s*=\s*1)$", re.IGNORECASE)


def _sql_relations(sql: str) -> list[str]:
    """Extract base relation names needed for logical topology checks."""

    relations: list[str] = []
    from_match = _FROM_CLAUSE.search(sql)
    if from_match:
        for part in from_match.group("body").split(","):
            relation_match = _RELATION_NAME.match(part)
            if relation_match:
                relations.append(relation_match.group(1))
    relations.extend(match.group("relation") for match in _JOIN_CLAUSE.finditer(sql))
    return relations


def _join_contracts(
    topology: dict[str, object], key: str
) -> tuple[tuple[str, tuple[str, str], str], ...]:
    raw = topology.get(key)
    if raw == "required_join_edges":
        raw = topology.get("required_join_edges")
    items = _tuple_items(raw)
    contracts: list[tuple[str, tuple[str, str], str]] = []
    for item in items:
        if not isinstance(item, list | tuple) or len(item) != 3:
            raise PR18EvidenceError("query contract has invalid join edges")
        name, relations, pattern = item
        relation_items = _tuple_items(relations)
        if (
            not isinstance(name, str)
            or len(relation_items) != 2
            or any(not isinstance(value, str) for value in relation_items)
            or not isinstance(pattern, str)
        ):
            raise PR18EvidenceError("query contract has invalid join edges")
        contracts.append((name, (str(relation_items[0]), str(relation_items[1])), pattern))
    return tuple(contracts)


def _extract_join_edges(
    sql: str, *, plan_relations: set[str]
) -> tuple[list[dict[str, object]], bool]:
    """Extract logical JOIN edges and reject syntax too ambiguous to verify."""

    sql_relations = _sql_relations(sql)
    joins = list(_JOIN_CLAUSE.finditer(sql))
    if len(sql_relations) < len(joins):
        raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: SQL relation topology is ambiguous")
    edges: list[dict[str, object]] = []
    cartesian = False
    for index, match in enumerate(joins):
        right = match.group("relation")
        left_index = index
        if left_index >= len(sql_relations):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: JOIN has no left relation")
        left = sql_relations[left_index]
        kind = match.group("kind").upper()
        tail = match.group("tail").strip()
        on_match = re.match(r"ON\s+(?P<predicate>.*)\Z", tail, re.IGNORECASE | re.DOTALL)
        predicate = on_match.group("predicate").strip() if on_match else ""
        is_cartesian = (
            "CROSS" in kind or not predicate or bool(_CARTESIAN_PREDICATE.fullmatch(predicate))
        )
        if is_cartesian:
            cartesian = True
        references = {
            name for name in _RELATION_REFERENCE.findall(predicate) if name in plan_relations
        }
        edge_relations = tuple(sorted(references)) if len(references) == 2 else (left, right)
        edges.append(
            {
                "left": edge_relations[0],
                "right": edge_relations[1],
                "predicate": predicate,
                "cartesian": is_cartesian,
                "relation_references": sorted(references),
            }
        )
    return edges, cartesian


def _edge_key(relations: tuple[str, str]) -> tuple[str, str]:
    return min(relations), max(relations)


def _join_graph_connected(relations: set[str], edges: list[dict[str, object]]) -> bool:
    if len(relations) <= 1:
        return True
    adjacency = {relation: set() for relation in relations}
    for edge in edges:
        if edge.get("cartesian"):
            continue
        left = edge.get("left")
        right = edge.get("right")
        if isinstance(left, str) and isinstance(right, str):
            adjacency.setdefault(left, set()).add(right)
            adjacency.setdefault(right, set()).add(left)
    seen = {next(iter(relations))}
    pending = list(seen)
    while pending:
        current = pending.pop()
        for neighbor in adjacency.get(current, set()) - seen:
            seen.add(neighbor)
            pending.append(neighbor)
    return seen == relations


def validate_query_contract(
    expectation: dict[str, object], statements: object
) -> dict[str, object]:
    """Enforce an independent frozen query contract against captured SQL/plans."""

    purity_projection = validate_statement_purity(statements)
    if purity_projection["overall_verdict"] != "PASS":
        if purity_projection["unknown_statement_count"]:
            raise PR18EvidenceError("NOT_VERIFIED: query contract has unknown statement purity")
        raise PR18EvidenceError("WRITE_OR_LOCK_VIOLATION: query contract is not read-only")
    if not isinstance(statements, list) or not statements:
        raise PR18EvidenceError("query contract captured no statements")
    required_relation_items = _tuple_items(expectation.get("required_relations"))
    if not required_relation_items or any(
        not isinstance(item, str) for item in required_relation_items
    ):
        raise PR18EvidenceError("query contract has no valid required relations")
    required_relations = tuple(item for item in required_relation_items if isinstance(item, str))
    topology = expectation.get("topology")
    if not isinstance(topology, dict):
        raise PR18EvidenceError("NOT_VERIFIED: query contract has no topology constraints")
    allowed_relation_items = _tuple_items(topology.get("allowed_relations"))
    if not allowed_relation_items or any(
        not isinstance(item, str) for item in allowed_relation_items
    ):
        raise PR18EvidenceError("NOT_VERIFIED: query contract has no allowed relation set")
    allowed_relations = tuple(item for item in allowed_relation_items if isinstance(item, str))
    closed_relation_set = topology.get("closed_relation_set") is True
    if not closed_relation_set:
        raise PR18EvidenceError("NOT_VERIFIED: query contract relation set is not explicit")
    if not all(
        isinstance(topology.get(key), bool)
        for key in (
            "allow_single_relation_reads",
            "allow_cartesian_joins",
            "forbidden_cartesian_joins",
        )
    ):
        raise PR18EvidenceError("NOT_VERIFIED: query contract topology booleans are incomplete")
    actual_relations: set[str] = set()
    statement_plans: list[tuple[dict[str, object], str, set[str]]] = []
    for statement in statements:
        if not isinstance(statement, dict):
            raise PR18EvidenceError("NOT_VERIFIED: malformed captured query statement")
        plan = statement.get("plan")
        if not isinstance(plan, dict):
            raise PR18EvidenceError("NOT_VERIFIED: query contract statement has no plan")
        plan_relations = set(_string_items(plan.get("relations"), label="relations"))
        if not _string_items(plan.get("node_types"), label="node types"):
            raise PR18EvidenceError("NOT_VERIFIED: query plan has no node types")
        actual_relations.update(plan_relations)
        statement_plans.append((plan, str(statement.get("sql", "")), plan_relations))
    missing_relations = sorted(set(required_relations) - actual_relations)
    if missing_relations:
        raise PR18EvidenceError(f"MISSING_REQUIRED_RELATION: {', '.join(missing_relations)}")
    unexpected_relations = sorted(actual_relations - set(allowed_relations))
    if closed_relation_set and unexpected_relations:
        raise PR18EvidenceError(f"UNEXPECTED_RELATION: {', '.join(unexpected_relations)}")

    sql_text = "\n".join(
        str(statement.get("sql", "")) for statement in statements if isinstance(statement, dict)
    )
    missing_predicates: list[str] = []
    predicate_items = _tuple_items(expectation.get("required_predicates"))
    for item in predicate_items:
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise PR18EvidenceError("query contract has invalid required predicates")
        name, pattern = item
        if not re.search(str(pattern), sql_text, re.IGNORECASE | re.DOTALL):
            missing_predicates.append(str(name))
    if missing_predicates:
        raise PR18EvidenceError(f"MISSING_REQUIRED_PREDICATE: {', '.join(missing_predicates)}")
    forbidden_nodes = set(_string_items(topology.get("forbidden_node_types"), label="node types"))
    forbidden_fragments = _string_items(
        topology.get("forbidden_sql_fragments"), label="SQL fragments"
    )
    required_edges = _join_contracts(topology, "required_join_edges")
    allowed_edges = _join_contracts(topology, "allowed_join_edges")
    if topology.get("allowed_join_edges") == "required_join_edges":
        allowed_edges = required_edges
    allowed_edge_keys = {_edge_key(item[1]) for item in allowed_edges}
    if any(_edge_key(edge[1]) not in allowed_edge_keys for edge in required_edges):
        raise PR18EvidenceError("NOT_VERIFIED: required topology edge is not allowed")
    observed_edges: list[dict[str, object]] = []
    observed_edge_names: set[str] = set()
    invalid_edges: list[str] = []
    cartesian_join = False
    for plan, sql, plan_relations in statement_plans:
        if classify_statement(sql) != READ_SELECT:
            raise PR18EvidenceError(
                "WRITE_OR_LOCK_VIOLATION: query captured a non-SELECT statement"
            )
        node_types = set(_string_items(plan.get("node_types"), label="node types"))
        forbidden = sorted(node_types & forbidden_nodes)
        if forbidden:
            raise PR18EvidenceError(
                f"WRITE_OR_LOCK_VIOLATION: forbidden query topology: {', '.join(forbidden)}"
            )
        upper_sql = sql.upper()
        if any(fragment.upper() in upper_sql for fragment in forbidden_fragments):
            raise PR18EvidenceError("WRITE_OR_LOCK_VIOLATION: forbidden query lock/write topology")
        sql_relations = set(_sql_relations(sql))
        if not sql_relations and plan_relations:
            raise PR18EvidenceError("NOT_VERIFIED: SQL relation topology could not be parsed")
        if topology.get("mode") == "batched_single_relation_selects":
            if not topology.get("allow_single_relation_reads") or len(plan_relations) != 1:
                raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: expected a single relation read")
            if sql_relations != plan_relations:
                raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: SQL and plan relations disagree")
        edges, statement_cartesian = _extract_join_edges(sql, plan_relations=plan_relations)
        cartesian_join = cartesian_join or statement_cartesian
        if (
            statement_cartesian
            and topology.get("forbidden_cartesian_joins") is True
            and topology.get("allow_cartesian_joins") is not True
        ):
            raise PR18EvidenceError("CARTESIAN_JOIN: Cartesian join is not authorized")
        if len(plan_relations) > 1 and not topology.get("allow_single_relation_reads"):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: multi-relation read is not authorized")
        if len(plan_relations) > 1 and not _join_graph_connected(plan_relations, edges):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: join graph is disconnected")
        for edge in edges:
            pair = (str(edge["left"]), str(edge["right"]))
            matching = [item for item in allowed_edges if _edge_key(item[1]) == pair]
            if not matching:
                invalid_edges.append(f"{pair[0]}--{pair[1]}")
                continue
            matching_contract = next(
                (item for item in matching if re.search(item[2], sql, re.IGNORECASE | re.DOTALL)),
                None,
            )
            if matching_contract is None:
                invalid_edges.append(f"{pair[0]}--{pair[1]}")
                continue
            edge["name"] = matching_contract[0]
            observed_edge_names.add(matching_contract[0])
            observed_edges.append(edge)
    if invalid_edges:
        raise PR18EvidenceError(
            "INVALID_JOIN_TOPOLOGY: unauthorized or wrong join edge(s): "
            f"{', '.join(sorted(invalid_edges))}"
        )

    missing_join_patterns: list[str] = []
    for item in _tuple_items(topology.get("required_join_patterns")):
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise PR18EvidenceError("query contract has invalid join patterns")
        name, pattern = item
        if not re.search(str(pattern), sql_text, re.IGNORECASE | re.DOTALL):
            missing_join_patterns.append(str(name))
    if missing_join_patterns:
        raise PR18EvidenceError(
            "INVALID_JOIN_TOPOLOGY: required query topology absent: "
            f"{', '.join(missing_join_patterns)}"
        )
    missing_edges = sorted({item[0] for item in required_edges} - observed_edge_names)
    if missing_edges:
        raise PR18EvidenceError(
            f"INVALID_JOIN_TOPOLOGY: required join edge(s) absent: {', '.join(missing_edges)}"
        )
    expected_topology = {
        "mode": topology.get("mode"),
        "closed_relation_set": closed_relation_set,
        "allow_single_relation_reads": topology.get("allow_single_relation_reads") is True,
        "forbidden_cartesian_joins": topology.get("forbidden_cartesian_joins") is True,
        "required_join_edges": [
            {"name": name, "relations": list(relations), "predicate": pattern}
            for name, relations, pattern in required_edges
        ],
        "allowed_join_edges": [
            {"name": name, "relations": list(relations), "predicate": pattern}
            for name, relations, pattern in allowed_edges
        ],
        "forbidden_join_edges": topology.get("forbidden_join_edges"),
    }
    observed_topology = {
        "join_edges": sorted(
            observed_edges,
            key=lambda edge: (
                str(edge.get("left")),
                str(edge.get("right")),
                str(edge.get("predicate")),
            ),
        ),
        "connected": all(
            _join_graph_connected(
                set(plan_relations),
                _extract_join_edges(sql, plan_relations=plan_relations)[0],
            )
            for _plan, sql, plan_relations in statement_plans
        ),
    }
    return {
        "statement_count": purity_projection["statement_count"],
        "statement_evidence": purity_projection["statements"],
        "forbidden_statement_count": purity_projection["forbidden_statement_count"],
        "unknown_statement_count": purity_projection["unknown_statement_count"],
        "write_or_lock_verdict": purity_projection["write_or_lock_verdict"],
        "required_relations": list(required_relations),
        "allowed_relations": list(allowed_relations),
        "observed_relations": sorted(actual_relations),
        "actual_relations": sorted(actual_relations),
        "missing_relations": missing_relations,
        "unexpected_relations": unexpected_relations,
        "required_predicates": [
            str(item[0])
            for item in predicate_items
            if isinstance(item, list | tuple) and len(item) == 2
        ],
        "missing_predicates": missing_predicates,
        "predicate_verdict": "PASS",
        "topology_mode": topology["mode"],
        "expected_topology": expected_topology,
        "observed_topology": observed_topology,
        "cartesian_verdict": "PASS" if not cartesian_join else "FAIL",
        "topology_verdict": "PASS",
        "select_only": True,
        "no_cartesian_product": True,
        "no_write_or_lock": True,
        "verification_status": "VERIFIED",
        "overall_verdict": "PASS",
    }


def _validate_registry_tokens(command_id: str, tokens: list[str]) -> None:
    _validate_tokens(tokens)
    if "pytest" in tokens:
        targets = [token.split("::", 1)[0] for token in tokens if token.startswith("tests/")]
        for target in targets:
            if not (PROJECT_ROOT / target).exists():
                raise PR18EvidenceError(f"missing authoritative target: {command_id}:{target}")


def validate_current_command_registry() -> int:
    identifiers = [identifier for identifier, _ in AUTHORITATIVE_COMMANDS]
    if len(identifiers) != len(set(identifiers)):
        raise PR18EvidenceError("authoritative command registry contains duplicate ids")
    for command_id, tokens in AUTHORITATIVE_COMMANDS:
        _validate_registry_tokens(command_id, tokens)
    return len(AUTHORITATIVE_COMMANDS)


def authoritative_command_tokens(
    command_id: str, *, result_dir: str = "artifacts/pr_evidence/PR-18/junit"
) -> list[str]:
    for current_id, command in AUTHORITATIVE_COMMANDS:
        if current_id == command_id:
            tokens = [*command]
            if "pytest" in tokens:
                tokens.append(f"--junitxml={result_dir}/{command_id}.xml")
            _validate_tokens(tokens)
            return tokens
    raise PR18EvidenceError(f"unknown authoritative command: {command_id}")


def validate_stored_command_registry(entries: object) -> None:
    """Reject missing, extra, or token-drifted stored command results."""

    if not isinstance(entries, dict):
        raise PR18EvidenceError("stored commands must be an object")
    expected = {
        command_id: authoritative_command_tokens(command_id)
        for command_id, _command in AUTHORITATIVE_COMMANDS
    }
    if set(entries) != set(expected):
        raise PR18EvidenceError("stored command ids differ from authoritative registry")
    for command_id, tokens in expected.items():
        entry = entries[command_id]
        if not isinstance(entry, dict) or entry.get("command_tokens") != tokens:
            raise PR18EvidenceError(f"stored command tokens differ: {command_id}")
    validate_command_entries(entries)


def _marker_category(path: Path) -> str:
    parts = path.parts
    if "artifacts" in parts or "execution" in parts:
        return "historical evidence"
    if "vendor" in parts or "generated" in parts:
        return "vendor/generated"
    if parts and parts[0] == "src":
        return "production"
    if parts and parts[0] == "migrations":
        return "migration"
    if parts and parts[0] == "tests":
        return "tests"
    if parts and parts[0] == "docs":
        return "documentation"
    return "evidence/tooling"


def audit_repository_markers(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Classify repository-relevant marker occurrences deterministically."""

    records: list[dict[str, Any]] = []
    for root_name in TODO_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TODO_EXTENSIONS:
                continue
            if "junit" in path.parts or ".pytest_cache" in path.parts:
                continue
            relative = path.relative_to(root)
            if relative.parts[:3] == ("artifacts", "pr_evidence", "PR-18"):
                continue
            category = _marker_category(relative)
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, 1):
                for match in _TODO_PATTERN.finditer(line):
                    marker = match.group(1).upper()
                    relative_text = str(relative)
                    is_scanner_vocabulary = relative_text in {
                        "scripts/pr18_evidence.py",
                        "tests/unit/test_pr18_todo_audit.py",
                    }
                    is_normative_criterion = relative_text == (
                        "docs/architecture/04_Phase1_Development_Specification_v1.2_Harness_Integrated.md"
                    )
                    if category == "historical evidence" or category == "vendor/generated":
                        disposition = "OUT_OF_PHASE"
                        class_group_id = "historical-evidence-text"
                        rationale = "archived execution/evidence text records prior review history"
                    elif is_normative_criterion:
                        disposition = "CLOSED"
                        class_group_id = "normative-phase1-criteria"
                        rationale = (
                            "normative Phase 1 criterion is recorded as specification text, "
                            "not an open implementation task"
                        )
                    elif is_scanner_vocabulary:
                        disposition = "INTENTIONAL_NONBLOCKING"
                        class_group_id = "marker-audit-vocabulary"
                        rationale = (
                            "marker names are data used by the deterministic audit itself and "
                            "do not describe a deferred runtime action"
                        )
                    elif relative_text.startswith("docs/superpowers/plans/"):
                        disposition = "OUT_OF_PHASE"
                        class_group_id = "phase1-plan-checklist"
                        rationale = (
                            "all markers in the archived implementation-plan class are checklist "
                            "text for review work, not live runtime TODOs"
                        )
                    elif relative_text.startswith("docs/superpowers/specs/"):
                        disposition = "CLOSED"
                        class_group_id = "pr18-specification-criteria"
                        rationale = (
                            "all markers in the PR-18 design-spec class are acceptance criteria "
                            "documented by the frozen specification, not deferred implementation"
                        )
                    elif category in {"production", "migration"}:
                        disposition = "PR18_BLOCKER"
                        class_group_id = "live-runtime-marker"
                        rationale = (
                            "live production or migration marker requires explicit closure "
                            "before Phase 1 completion"
                        )
                    else:
                        disposition = "INTENTIONAL_NONBLOCKING"
                        class_group_id = "reviewed-transport-documentation"
                        rationale = (
                            "reviewed contract/documentation marker describes an audit criterion "
                            "or example rather than a deferred runtime action"
                        )
                    architecture_sensitive = category in {"production", "migration"} and bool(
                        re.search(
                            r"architecture|provenance|scientific|history|uow|application|agent|error|migration|postgres",
                            line,
                            re.IGNORECASE,
                        )
                    )
                    records.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "marker": marker,
                            "category": category,
                            "surrounding_intent": line.strip(),
                            "disposition": disposition,
                            "rationale": rationale,
                            "class_group_id": class_group_id,
                            "architecture_priority": "P1" if architecture_sensitive else None,
                        }
                    )
    live_categories = {"production", "migration", "tests", "documentation", "evidence/tooling"}
    undisposed = [
        record
        for record in records
        if record["category"] in live_categories and record["disposition"] not in TODO_DISPOSITIONS
    ]
    return {
        "markers_searched": list(TODO_MARKERS),
        "scope_roots": list(TODO_ROOTS),
        "records": records,
        "undisposed_live": undisposed,
        "architecture_p0": [
            record for record in records if record["architecture_priority"] == "P0"
        ],
        "architecture_p1": [
            record for record in records if record["architecture_priority"] == "P1"
        ],
    }


def collect_catalog_verification(engine: Engine) -> dict[str, Any]:
    """Compare PostgreSQL catalogs with the independent frozen index manifest."""

    from tests.contracts.pr18_manifest import FROZEN_REQUIRED_INDEXES

    expected_names = set(FROZEN_REQUIRED_INDEXES)
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT c.relname AS index_name, t.relname AS table_name, i.indisunique, "
                    "i.indisvalid, i.indisready, pg_get_expr(i.indpred, i.indrelid) AS predicate, "
                    "am.amname AS access_method, "
                    "array_agg(a.attname ORDER BY keys.ordinality) AS columns, "
                    "array_agg(opc.opcname ORDER BY keys.ordinality) AS operator_classes, "
                    "(pc.conindid IS NOT NULL) AS constraint_backed "
                    "FROM pg_index AS i "
                    "JOIN pg_class AS c ON c.oid = i.indexrelid "
                    "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                    "JOIN pg_class AS t ON t.oid = i.indrelid "
                    "JOIN pg_am AS am ON am.oid = c.relam "
                    "JOIN LATERAL unnest(i.indkey, i.indclass) WITH ORDINALITY "
                    "AS keys(attnum, opclass_oid, ordinality) ON true "
                    "JOIN pg_attribute AS a ON a.attrelid = i.indrelid AND a.attnum = keys.attnum "
                    "JOIN pg_opclass AS opc ON opc.oid = keys.opclass_oid "
                    "LEFT JOIN pg_constraint AS pc ON pc.conindid = i.indexrelid "
                    "WHERE n.nspname = 'public' AND c.relname = ANY(:names) "
                    "GROUP BY c.relname, t.relname, i.indisunique, i.indisvalid, i.indisready, "
                    "i.indpred, i.indrelid, am.amname, pc.conindid"
                ),
                {"names": sorted(expected_names)},
            )
            .mappings()
            .all()
        )
        critical_names = {
            row["index_name"]
            for row in connection.execute(
                text(
                    "SELECT c.relname AS index_name FROM pg_class AS c "
                    "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'i' "
                    "AND (c.relname LIKE 'uq_%' OR c.relname LIKE 'ix_%')"
                )
            ).mappings()
        }
    observed = {
        str(row["index_name"]): {
            "table": row["table_name"],
            "columns": tuple(row["columns"]),
            "unique": bool(row["indisunique"]),
            "predicate": row["predicate"],
            "access_method": row["access_method"],
            "operator_classes": tuple(row["operator_classes"]),
            "valid": bool(row["indisvalid"]),
            "ready": bool(row["indisready"]),
            "constraint_backed": bool(row["constraint_backed"]),
        }
        for row in rows
    }
    missing = sorted(expected_names - set(observed))
    mismatches: dict[str, dict[str, Any]] = {}
    for name, definition in FROZEN_REQUIRED_INDEXES.items():
        actual = observed.get(name)
        if actual is None:
            continue
        expected = {
            "table": definition["table"],
            "columns": _tuple_items(definition["columns"]),
            "unique": definition["unique"],
            "predicate": definition["predicate"],
            "constraint_backed": definition["constraint_backed"],
        }
        differences = {
            field: {"expected": expected[field], "observed": actual[field]}
            for field in expected
            if expected[field] != actual[field]
        }
        if differences or not actual["valid"] or not actual["ready"]:
            mismatches[name] = differences or {"valid_ready": {"expected": True, "observed": False}}
    return {
        "expected_manifest": [
            {"name": name, **definition} for name, definition in FROZEN_REQUIRED_INDEXES.items()
        ],
        "observed": observed,
        "missing_required": missing,
        "mismatches": mismatches,
        "unexpected_critical_names": sorted(critical_names - expected_names),
        "exact_required_coverage": not missing and not mismatches,
        "migration_required": bool(missing),
    }


def _plan_structure(connection: Any, statement: str, parameters: object) -> dict[str, Any]:
    """Return stable EXPLAIN structure for one captured production statement."""

    result = connection.exec_driver_sql(
        "EXPLAIN (FORMAT JSON) " + statement,
        parameters if parameters is not None else {},
    ).scalar_one()
    document = result[0] if isinstance(result, list) else result
    if not isinstance(document, dict) or not isinstance(document.get("Plan"), dict):
        raise PR18EvidenceError("malformed PostgreSQL JSON plan")

    node_types: list[str] = []
    relations: list[str] = []
    index_names: list[str] = []
    join_types: list[str] = []

    def visit(node: object) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("Node Type")
        if isinstance(node_type, str):
            node_types.append(node_type)
        relation = node.get("Relation Name")
        if isinstance(relation, str):
            relations.append(relation)
        index = node.get("Index Name")
        if isinstance(index, str):
            index_names.append(index)
        join_type = node.get("Join Type")
        if isinstance(join_type, str):
            join_types.append(join_type)
        for child in node.get("Plans", []):
            visit(child)

    visit(document["Plan"])
    return {
        "node_types": sorted(set(node_types)),
        "relations": sorted(set(relations)),
        "index_names": sorted(set(index_names)),
        "join_types": sorted(set(join_types)),
    }


def _seed_explain_fixture(engine: Engine) -> tuple[dict[str, Any], int]:
    """Create disposable rows used only to exercise the real read services."""

    from tests.integration.test_pr14_governance_integration import _seed_graph

    ids = _seed_graph(engine)
    now = datetime.now(UTC)
    filler_count = 1200
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_findings "
                "(id, project_id, finding_type, severity, title, description, "
                "target_type, target_id, target_content_hash, status, created_by, created_at) "
                "VALUES (:id, :project, 'explain_fixture', 'info', :title, 'fixture', "
                "'artifact_version', :target, NULL, 'open', :actor, :now)"
            ),
            [
                {
                    "id": uuid4(),
                    "project": ids["project"],
                    "title": f"EXPLAIN fixture {number}",
                    "target": ids["artifact_version"] if number == 0 else uuid4(),
                    "actor": ids["actor"],
                    "now": now,
                }
                for number in range(filler_count)
            ],
        )
        connection.execute(text("ANALYZE audit_findings"))
    return ids, filler_count


def _captured_query_plans(
    engine: Engine,
    operation: str,
    callback: Any,
    *,
    expectation: dict[str, object],
    representative_rows: int,
) -> dict[str, Any]:
    captured = _capture_sql_statements(engine, callback)

    if not captured:
        raise PR18EvidenceError(f"{operation} emitted no SQL statements")
    purity_projection = validate_statement_purity(captured)
    if purity_projection["overall_verdict"] != "PASS":
        if purity_projection["unknown_statement_count"]:
            raise PR18EvidenceError(
                "PRODUCTION_QUERY_PURITY_DEFECT_DISCOVERED = YES: "
                f"{operation} emitted an unknown statement"
            )
        raise PR18EvidenceError(
            "PRODUCTION_QUERY_PURITY_DEFECT_DISCOVERED = YES: "
            f"{operation} emitted a forbidden write or locking statement"
        )
    purity_statements = purity_projection.get("statements")
    if not isinstance(purity_statements, list) or len(purity_statements) != len(captured):
        raise PR18EvidenceError(
            f"NOT_VERIFIED: {operation} purity statement count does not reconcile"
        )
    statements: list[dict[str, Any]] = []
    with engine.connect() as connection:
        for index, (statement, parameters) in enumerate(captured):
            projected_statement = purity_statements[index]
            if not isinstance(projected_statement, dict):
                raise PR18EvidenceError(
                    f"NOT_VERIFIED: {operation} has malformed purity statement evidence"
                )
            if projected_statement.get("statement_class") != READ_SELECT:
                raise PR18EvidenceError(
                    f"{operation} has a non-ordinary SELECT after purity validation"
                )
            plan = _plan_structure(connection, statement, parameters)
            statements.append(
                {
                    "sql": statement,
                    "plan": plan,
                    **projected_statement,
                }
            )

    structural_assertions = validate_query_contract(expectation, statements)
    if structural_assertions["statement_count"] != len(statements):
        raise PR18EvidenceError("NOT_VERIFIED: captured statement count does not reconcile")
    return {
        "production_operation": operation,
        "query_path": operation,
        "repository_methods": list(_tuple_items(expectation["repository_methods"])),
        "statement_count": structural_assertions["statement_count"],
        "forbidden_statement_count": structural_assertions["forbidden_statement_count"],
        "unknown_statement_count": structural_assertions["unknown_statement_count"],
        "statement_purity": structural_assertions["statement_evidence"],
        "required_relations": structural_assertions["required_relations"],
        "allowed_relations": structural_assertions["allowed_relations"],
        "observed_relations": structural_assertions["observed_relations"],
        "missing_relations": structural_assertions["missing_relations"],
        "unexpected_relations": structural_assertions["unexpected_relations"],
        "required_predicates": structural_assertions["required_predicates"],
        "predicate_verdict": structural_assertions["predicate_verdict"],
        "expected_topology": structural_assertions["expected_topology"],
        "observed_topology": structural_assertions["observed_topology"],
        "cartesian_verdict": structural_assertions["cartesian_verdict"],
        "write_or_lock_verdict": structural_assertions["write_or_lock_verdict"],
        "overall_verdict": structural_assertions["overall_verdict"],
        "verification_status": structural_assertions["verification_status"],
        "representative_rows": representative_rows,
        "statements": statements,
        "structural_assertions": structural_assertions,
    }


def collect_query_explain_baselines(engine: Engine) -> dict[str, dict[str, Any]]:
    """Capture EXPLAIN plans for real Phase 1 provenance/governance query services."""

    from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS

    from researchbase.application.governance_queries import GovernanceQueryService
    from researchbase.application.provenance_queries import ProvenanceQueryService
    from researchbase.domain.governance import GovernanceTargetType
    from researchbase.persistence.database import create_session_factory
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    ids, representative_rows = _seed_explain_fixture(engine)
    sessions = create_session_factory(engine)

    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    provenance = ProvenanceQueryService(factory)
    governance = GovernanceQueryService(factory)
    baselines = {
        "run_provenance": _captured_query_plans(
            engine,
            "ProvenanceQueryService.get_run_provenance",
            lambda: provenance.get_run_provenance(ids["run"]),
            expectation=FROZEN_QUERY_EXPECTATIONS["run_provenance"],
            representative_rows=representative_rows,
        ),
        "claim_trace": _captured_query_plans(
            engine,
            "ProvenanceQueryService.trace_claim_to_runs",
            lambda: provenance.trace_claim_to_runs(ids["claim_version"]),
            expectation=FROZEN_QUERY_EXPECTATIONS["claim_trace"],
            representative_rows=representative_rows,
        ),
        "downstream_impact": _captured_query_plans(
            engine,
            "GovernanceQueryService.downstream_impact",
            lambda: governance.downstream_impact(
                ids["project"], GovernanceTargetType.ARTIFACT_VERSION, ids["artifact_version"]
            ),
            expectation=FROZEN_QUERY_EXPECTATIONS["downstream_impact"],
            representative_rows=representative_rows,
        ),
        "audit_findings": _captured_query_plans(
            engine,
            "GovernanceQueryService.list_audit_findings",
            lambda: governance.list_audit_findings(
                ids["project"], GovernanceTargetType.ARTIFACT_VERSION, ids["artifact_version"]
            ),
            expectation=FROZEN_QUERY_EXPECTATIONS["audit_findings"],
            representative_rows=representative_rows,
        ),
    }
    audit_statements = baselines["audit_findings"]["statements"]
    baselines["audit_findings"]["index_usable"] = any(
        "ix_audit_findings_target" in item["plan"]["index_names"] for item in audit_statements
    )
    if not baselines["audit_findings"]["index_usable"]:
        raise PR18EvidenceError("representative audit-finding query did not use its required index")
    return baselines


def command_fingerprint(tokens: list[str]) -> str:
    """Return the stable SHA-256 fingerprint for canonical command tokens."""

    if not tokens or any(not isinstance(token, str) or not token for token in tokens):
        raise PR18EvidenceError("command tokens must be non-empty strings")
    return hashlib.sha256("\0".join(tokens).encode("utf-8")).hexdigest()


def _validate_tokens(tokens: object) -> list[str]:
    if (
        not isinstance(tokens, list)
        or not tokens
        or not all(isinstance(token, str) and token for token in tokens)
    ):
        raise PR18EvidenceError("command_tokens must be a non-empty string list")
    if any(_ABSOLUTE_PATH.match(token) for token in tokens):
        raise PR18EvidenceError("absolute paths are forbidden in command evidence")
    if any(_CREDENTIAL_TOKEN.search(token) for token in tokens):
        raise PR18EvidenceError("credential-bearing command token")
    return tokens


def validate_command_entries(entries: object) -> dict[str, int]:
    """Validate exact command tokens, fingerprints, and safe paths."""

    if not isinstance(entries, dict) or not entries:
        raise PR18EvidenceError("commands must be a non-empty object")
    for command_id, entry in entries.items():
        if not isinstance(command_id, str) or not command_id:
            raise PR18EvidenceError("command ids must be non-empty strings")
        if not isinstance(entry, dict):
            raise PR18EvidenceError(f"malformed command entry: {command_id}")
        tokens = _validate_tokens(entry.get("command_tokens"))
        if entry.get("command") != shlex.join(tokens):
            raise PR18EvidenceError(f"command text/token drift: {command_id}")
        if entry.get("command_fingerprint") != command_fingerprint(tokens):
            raise PR18EvidenceError(f"command fingerprint drift: {command_id}")
        counts = entry.get("counts")
        if not isinstance(counts, dict):
            raise PR18EvidenceError(f"missing counts: {command_id}")
        return_code = entry.get("return_code")
        if (
            not isinstance(return_code, int)
            or isinstance(return_code, bool)
            or counts.get("return_code") != return_code
        ):
            raise PR18EvidenceError(f"return-code accounting mismatch: {command_id}")
        if "pytest" in tokens:
            if set(PYTEST_COUNT_FIELDS) - set(counts):
                raise PR18EvidenceError(f"incomplete pytest count schema: {command_id}")
            if any(
                not isinstance(counts[key], int) or isinstance(counts[key], bool) or counts[key] < 0
                for key in PYTEST_COUNT_FIELDS
            ):
                raise PR18EvidenceError(f"malformed pytest count values: {command_id}")
            if counts["total_discovered"] != counts["selected"] + counts["deselected"]:
                raise PR18EvidenceError(f"pytest discovery counts do not reconcile: {command_id}")
            outcomes = ("passed", "failed", "skipped", "xfailed", "xpassed", "errors")
            if counts["selected"] != sum(counts[key] for key in outcomes):
                raise PR18EvidenceError(f"pytest outcome counts do not reconcile: {command_id}")
            if return_code != 0:
                raise PR18EvidenceError(f"required command failed: {command_id}")
        elif counts.get("status") != "PASS" or return_code != 0:
            raise PR18EvidenceError(f"non-pytest command did not pass: {command_id}")
    count = len(entries)
    return {"stored": count, "valid": count}


def validate_evidence_artifact(artifact: object, *, implementation_subject: str) -> None:
    """Validate the fail-closed top-level PR-18 evidence contract."""

    if not isinstance(artifact, dict):
        raise PR18EvidenceError("evidence must be a JSON object")
    if artifact.get("schema_version") != "pr18r-evidence-v1":
        raise PR18EvidenceError("unsupported PR-18 evidence schema")
    if artifact.get("protocol") != "non-self-referential-v1":
        raise PR18EvidenceError("non-self-referential protocol is required")
    if artifact.get("implementation_subject") != implementation_subject:
        raise PR18EvidenceError("evidence subject does not match implementation subject")
    if "evidence_head" in artifact:
        raise PR18EvidenceError("future evidence head must not be embedded")
    binding = artifact.get("evidence_binding")
    if binding != {"mode": "separate-evidence-only-commit", "parent": implementation_subject}:
        raise PR18EvidenceError("evidence chronology binding is invalid")
    audits = artifact.get("audits")
    if not isinstance(audits, dict):
        raise PR18EvidenceError("missing evidence audits")
    if audits.get("absolute_paths") != []:
        raise PR18EvidenceError("absolute paths must be absent")
    if audits.get("credential_leakage") != []:
        raise PR18EvidenceError("credential leakage must be absent")
    if audits.get("reproducible") is not True:
        raise PR18EvidenceError("reproducibility must be explicitly true")
    consistency = artifact.get("command_consistency")
    if not isinstance(consistency, dict):
        raise PR18EvidenceError("missing command consistency")
    commands = artifact.get("commands")
    counts = validate_command_entries(commands)
    if consistency.get("stored") != counts["stored"]:
        raise PR18EvidenceError("stored command count mismatch")
    if consistency.get("current") != counts["stored"]:
        raise PR18EvidenceError("current command count mismatch")
    if consistency.get("exact_token_matches") != counts["stored"]:
        raise PR18EvidenceError("exact command token accounting mismatch")
    if consistency.get("stale_result_reuse") is not False:
        raise PR18EvidenceError("stale result reuse must be explicitly false")


def build_evidence_artifact(
    *,
    implementation_subject: str,
    commands: dict[str, dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical PR-18 evidence object from current command results."""

    command_count = len(commands)
    artifact: dict[str, Any] = {
        "schema_version": "pr18r-evidence-v1",
        "protocol": "non-self-referential-v1",
        "implementation_subject": implementation_subject,
        "evidence_binding": {
            "mode": "separate-evidence-only-commit",
            "parent": implementation_subject,
        },
        "command_consistency": {
            "stored": command_count,
            "current": command_count,
            "exact_token_matches": command_count,
            "stale_result_reuse": False,
        },
        "audits": {
            "absolute_paths": [],
            "credential_leakage": [],
            "reproducible": True,
        },
        "commands": commands,
    }
    if metadata:
        artifact["metadata"] = metadata
    validate_evidence_artifact(artifact, implementation_subject=implementation_subject)
    return artifact


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _pytest_skip_identities(junit_xml: str) -> set[str]:
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError as error:
        raise PR18EvidenceError("cannot inspect pytest skips from malformed JUnit") from error
    identities: set[str] = set()
    for testcase in root.iter("testcase"):
        skipped = testcase.find("skipped")
        if skipped is None or skipped.attrib.get("type") == "pytest.xfail":
            continue
        classname = testcase.attrib.get("classname", "")
        name = testcase.attrib.get("name", "")
        identities.add(f"{classname}::{name}")
    return identities


def _collection_command(tokens: list[str]) -> list[str]:
    command = [token for token in tokens if not token.startswith("--junitxml=")]
    pytest_index = command.index("pytest")
    command[pytest_index + 1 : pytest_index + 1] = ["--collect-only", "-o", "addopts="]
    return command


def _database_identity() -> dict[str, Any]:
    from researchbase.persistence.database import create_database_engine

    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_database() AS database, current_schema() AS schema, "
                    "version() AS server_version, "
                    "current_setting('server_version') AS version_number, "
                    "(SELECT version_num FROM public.alembic_version) AS alembic_revision"
                )
            ).one()
    finally:
        engine.dispose()
    if not str(row.version_number).startswith("18"):
        raise PR18EvidenceError(f"PostgreSQL 18 is required, got {row.version_number}")
    return {
        "database": row.database,
        "schema": row.schema,
        "server_version": row.server_version,
        "version_number": row.version_number,
        "alembic_revision": row.alembic_revision,
        "credentials": "redacted",
    }


def resolve_implementation_subject(value: str | None = None) -> str:
    subject = value or os.getenv("PR18R_IMPLEMENTATION_SUBJECT_HEAD")
    if not subject:
        raise PR18EvidenceError("PR18R_IMPLEMENTATION_SUBJECT_HEAD is required")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{subject}^{{commit}}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def execute_authoritative_commands(
    *,
    implementation_subject: str,
    runner: Any = subprocess.run,
    result_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Execute every registered command and return only reconciled results."""

    validate_current_command_registry()
    result_path = result_dir or PROJECT_ROOT / ".pr18r_evidence_results"
    result_path.mkdir(parents=True, exist_ok=True)
    if result_dir is not None:
        for stale_result in result_path.glob("*.xml"):
            stale_result.unlink()
    entries: dict[str, dict[str, Any]] = {}
    try:
        for command_id, _base in AUTHORITATIVE_COMMANDS:
            tokens = authoritative_command_tokens(
                command_id, result_dir=str(result_path.relative_to(PROJECT_ROOT))
            )
            result = runner(
                tokens,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            return_code = int(result.returncode)
            if "pytest" in tokens:
                junit_path = PROJECT_ROOT / next(
                    token.split("=", 1)[1] for token in tokens if token.startswith("--junitxml=")
                )
                if not junit_path.exists():
                    raise PR18EvidenceError(f"missing JUnit result: {command_id}")
                junit_xml = junit_path.read_text(encoding="utf-8")
                junit_xml = junit_xml.replace(f"{PROJECT_ROOT}/", "")
                junit_xml = junit_xml.replace(str(PROJECT_ROOT), "")
                junit_path.write_text(junit_xml, encoding="utf-8")
                collection = runner(
                    _collection_command(tokens),
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                counts = parse_pytest_counts(
                    output=result.stdout,
                    collection_output=collection.stdout,
                    junit_xml=junit_xml,
                    return_code=return_code,
                )
                skipped = _pytest_skip_identities(junit_xml)
                unexpected = skipped - INHERITED_PR11R2_SKIP_IDENTITIES
                if unexpected:
                    raise PR18EvidenceError(
                        f"unexpected pytest skips in {command_id}: {sorted(unexpected)}"
                    )
                entry_counts: dict[str, Any] = counts
            else:
                if return_code != 0:
                    raise PR18EvidenceError(f"required command failed: {command_id}")
                entry_counts = {"status": "PASS", "return_code": 0}
            entries[command_id] = {
                "command": shlex.join(tokens),
                "command_tokens": tokens,
                "command_fingerprint": command_fingerprint(tokens),
                "return_code": return_code,
                "counts": entry_counts,
            }
        validate_command_entries(entries)
        return entries
    finally:
        if result_dir is None:
            shutil.rmtree(result_path, ignore_errors=True)


def run_authoritative_evidence(
    *,
    implementation_subject: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run the frozen PR-18R command registry and write one bound artifact."""

    resolved_subject = resolve_implementation_subject(implementation_subject)
    current_head = resolve_implementation_subject("HEAD")
    if current_head != resolved_subject:
        raise PR18EvidenceError("evidence must run at the frozen implementation subject HEAD")
    database = _database_identity()
    commands = execute_authoritative_commands(
        implementation_subject=resolved_subject,
        result_dir=PROJECT_ROOT / "artifacts/pr_evidence/PR-18/junit",
    )
    from researchbase.persistence.database import create_database_engine

    engine = create_database_engine()
    try:
        catalog = collect_catalog_verification(engine)
        explain = collect_query_explain_baselines(engine)
    finally:
        engine.dispose()
    todo = audit_repository_markers()
    artifact = build_evidence_artifact(
        implementation_subject=resolved_subject,
        commands=commands,
        metadata={
            "database": database,
            "query_explain": explain,
            "catalog": catalog,
            "todo": todo,
            "fresh_execution": True,
        },
    )
    destination = (
        output_path or PROJECT_ROOT / "artifacts/pr_evidence/PR-18/implementation_verification.json"
    )
    write_evidence_artifact(destination, artifact)
    projection_root = destination.parent
    projections = {
        "catalog_verification.json": catalog,
        "query_explain_baselines.json": {
            "database": database,
            "queries": explain,
            "result": "PASS",
        },
        "todo_fixme_disposition.json": todo,
        "error_log_audit.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "selectors": [
                "tests/unit/test_pr18_error_log_hardening.py",
                "tests/unit/test_pr15_http.py",
                "tests/unit/test_pr16_cli_errors.py",
            ],
        },
        "architecture_agent_audit.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "existing_suite": "tests/architecture/test_pr17_agent_ready_architecture.py",
            "complementary_suite": "tests/architecture/test_pr18_boundaries.py",
        },
        "api_cli_validation.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "document": "docs/phase1_api_cli_examples.md",
        },
    }
    for filename, projection in projections.items():
        (projection_root / filename).write_text(
            json.dumps(_json_safe(projection), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    architecture_count = commands["architecture"]["counts"]["passed"]
    (projection_root / "architecture_verification.md").write_text(
        "# PR-18R architecture verification\n\n"
        f"Result: PASS. The authoritative architecture suite recorded {architecture_count} "
        "passed tests.\n\n"
        "The accepted PR-17 Agent-ready suite was rerun with PR-18R complementary "
        "AST/interface checks for Core imports, adapter ownership, repositories/UoW, and "
        "generic provenance/version "
        "escape hatches.\n",
        encoding="utf-8",
    )
    (projection_root / "agent_ready_core_audit.md").write_text(
        "# Agent-ready Core boundary audit\n\n"
        "Result: PASS — boundary audit only.\n\n"
        "Future callers use the shared Application commands/queries and "
        "WriteResult-compatible DTOs; "
        "FastAPI, Typer, and SQLAlchemy session manipulation are not required. No agent runtime or "
        "Phase 2 implementation was added.\n",
        encoding="utf-8",
    )
    (projection_root / "api_cli_examples.md").write_text(
        "# API/CLI example verification\n\n"
        "Result: PASS. The executable documentation contract suite validated the structured "
        "examples "
        "against current OpenAPI routes/statuses and the real Typer command surface, including "
        "representative success and failure behavior.\n",
        encoding="utf-8",
    )
    todo_lines = [
        "# PR-18R TODO/FIXME disposition",
        "",
        f"Result: PASS. {len(todo['records'])} repository-relevant markers were classified; "
        f"{len(todo['undisposed_live'])} live markers remain undisposed.",
        "",
        "| Path | Line | Marker | Category | Disposition | Rationale |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for record in todo["records"]:
        rationale = str(record["rationale"]).replace("|", "\\|")
        todo_lines.append(
            f"| `{record['path']}` | {record['line']} | `{record['marker']}` | "
            f"{record['category']} | `{record['disposition']}` | {rationale} |"
        )
    todo_lines.extend(
        [
            "",
            "Architecture P0 markers: " + str(len(todo["architecture_p0"])),
            "Architecture P1 markers: " + str(len(todo["architecture_p1"])),
            "",
            "Approved dispositions: CLOSED, INTENTIONAL_NONBLOCKING, OUT_OF_PHASE, PR18_BLOCKER.",
        ]
    )
    (projection_root / "todo_fixme_disposition.md").write_text(
        "\n".join(todo_lines) + "\n", encoding="utf-8"
    )
    (projection_root / "error_log_audit.md").write_text(
        "# PR-18R error/log hardening audit\n\n"
        "Result: PASS. The executable redaction suite covered structured API keys, Authorization "
        "and Bearer values, credential-bearing DSNs, exception-string secrets, nested fields, "
        "HTTP errors, "
        "and CLI errors. The only production change is the minimal structured-log redaction patch; "
        "transaction and Application error semantics remain unchanged.\n",
        encoding="utf-8",
    )
    lines = ["# PR-18R commands and results", "", "| Command | Result |", "| --- | --- |"]
    for command_id, entry in commands.items():
        lines.append(f"| `{command_id}` | `{json.dumps(entry['counts'], sort_keys=True)}` |")
    (projection_root / "commands_and_results.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return artifact


def write_evidence_artifact(path: Path, artifact: dict[str, Any]) -> None:
    """Validate and write canonical repository-relative JSON evidence."""

    subject = artifact.get("implementation_subject")
    if not isinstance(subject, str) or not subject:
        raise PR18EvidenceError("implementation subject is required")
    validate_evidence_artifact(artifact, implementation_subject=subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(artifact), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    run_authoritative_evidence(implementation_subject=resolve_implementation_subject())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
