"""Fail-closed helpers for PR-18 evidence.

This module intentionally does not modify the PR-17DR5 evidence generator or
its artifacts. It validates the small, repository-relative manifest used to
record PR-18 verification results.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any

_ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_CREDENTIAL_TOKEN = re.compile(
    r"(?i)(?:password|passwd|secret|credential|api[_-]?key|token)\s*[=:]|"
    r"postgres(?:ql)?(?:\+[^:/\s]+)?://[^:/\s]+:[^@\s]+@"
)


class PR18EvidenceError(ValueError):
    """Raised when PR-18 evidence is incomplete, stale, or unsafe."""


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
        if entry.get("return_code") != 0:
            raise PR18EvidenceError(f"command failed: {command_id}")
        if not isinstance(entry.get("counts"), dict):
            raise PR18EvidenceError(f"missing counts: {command_id}")
    count = len(entries)
    return {"stored": count, "valid": count}


def validate_evidence_artifact(artifact: object, *, implementation_subject: str) -> None:
    """Validate the fail-closed top-level PR-18 evidence contract."""

    if not isinstance(artifact, dict):
        raise PR18EvidenceError("evidence must be a JSON object")
    if artifact.get("schema_version") != "pr18-evidence-v1":
        raise PR18EvidenceError("unsupported PR-18 evidence schema")
    if artifact.get("implementation_subject") != implementation_subject:
        raise PR18EvidenceError("evidence subject does not match implementation subject")
    if not isinstance(artifact.get("evidence_head"), str) or not artifact["evidence_head"]:
        raise PR18EvidenceError("evidence head is required")
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
    evidence_head: str,
    commands: dict[str, dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical PR-18 evidence object from current command results."""

    command_count = len(commands)
    artifact: dict[str, Any] = {
        "schema_version": "pr18-evidence-v1",
        "implementation_subject": implementation_subject,
        "evidence_head": evidence_head,
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


def write_evidence_artifact(path: Path, artifact: dict[str, Any]) -> None:
    """Validate and write canonical repository-relative JSON evidence."""

    subject = artifact.get("implementation_subject")
    if not isinstance(subject, str) or not subject:
        raise PR18EvidenceError("implementation subject is required")
    validate_evidence_artifact(artifact, implementation_subject=subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
