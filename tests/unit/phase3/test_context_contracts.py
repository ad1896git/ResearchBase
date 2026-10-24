"""Adversarial closed-format vectors, including exact boundary sizes."""

from dataclasses import FrozenInstanceError, replace
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.context_contracts import (
    SourceReference,
    TaskMemoryManifest,
    parse_memory_manifest,
)
from researchbase.agent_runtime.application.contracts import InputType
from researchbase.agent_runtime.domain.task_memory import MemoryNotes, memory_material
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def manifest(**changes):
    values: dict[str, Any] = dict(
        project_scope=UUID(int=1),
        task_id=UUID(int=2),
        step_id=None,
        created_by=UUID(int=3),
        trust_level="UNVERIFIED",
        validity_status="UNASSESSED",
        notes=MemoryNotes(),
        source_refs=(),
    )
    values.update(changes)
    return TaskMemoryManifest(**values)


def encoded(value):
    return canonical_json_bytes(memory_material(value))


@pytest.mark.parametrize("kind", tuple(InputType))
def test_owning_hashes_round_trip_without_rehash(kind):
    ref = SourceReference(
        type=kind,
        id=UUID(int=9),
        content_hash="a" * 64,
        hash_scheme="sha256-cjson-v1"
        if kind in {InputType.SOURCE_VERSION, InputType.MANUSCRIPT_VERSION}
        else None,
    )
    value = manifest(source_refs=(ref,))
    assert parse_memory_manifest(encoded(value)) == value
    assert value.source_refs[0].content_hash == "a" * 64
    with pytest.raises(FrozenInstanceError):
        cast(Any, value).notes = MemoryNotes()


@pytest.mark.parametrize(
    "case", ["extra", "nested", "duplicate", "unknown", "nan", "uuid", "nfc", "keys"]
)
def test_recursive_malformed_format_rejected(case):
    value = memory_material(manifest())
    assert isinstance(value, dict)
    if case == "extra":
        value["approval"] = True
    if case == "nested":
        value["notes"] = {"plan_notes": [], "authority": True}
    if case == "duplicate":
        ref = dict(
            type="ARTIFACT_VERSION", id=str(UUID(int=5)), content_hash="a" * 64, hash_scheme=None
        )
        value["source_refs"] = [ref, ref]
    if case == "unknown":
        value["source_refs"] = [
            dict(type="RUN", id=str(UUID(int=5)), content_hash="a" * 64, hash_scheme=None)
        ]
    if case == "uuid":
        value["task_id"] = "00000000000000000000000000000002"
    if case == "nfc":
        value["notes"] = dict(plan_notes=["e\u0301"])
    raw = canonical_json_bytes(value)
    if case == "nan":
        raw = raw.replace(b'"format_version":1', b'"format_version":NaN')
    if case == "keys":
        raw = raw.replace(b'"format_version":1', b'"format_version":1,"format_version":1')
    with pytest.raises(ResearchBaseError) as caught:
        parse_memory_manifest(raw)
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


def test_note_source_and_encoded_bounds():
    assert manifest(notes=MemoryNotes(plan_notes=("é" * 8192,)))
    with pytest.raises(ValueError):
        MemoryNotes(plan_notes=("a" * 8193,))
    refs = tuple(
        SourceReference(
            type=InputType.ARTIFACT_VERSION,
            id=UUID(int=i + 1),
            content_hash="b" * 64,
            hash_scheme=None,
        )
        for i in range(257)
    )
    assert len(manifest(source_refs=refs[:256]).source_refs) == 256
    with pytest.raises(ValueError):
        manifest(source_refs=refs)
    with pytest.raises(ValueError):
        manifest(source_refs=tuple(reversed(refs[:2])))
    # Fill the envelope to exactly 1 MiB while keeping every individual note bounded.
    notes = ["x" * 8192] * 127
    base = encoded(manifest(notes=MemoryNotes(plan_notes=tuple(notes + [""]))))
    notes.append("x" * (1048576 - len(base)))
    exact = manifest(notes=MemoryNotes(plan_notes=tuple(notes)))
    assert len(encoded(exact)) == 1048576
    assert parse_memory_manifest(encoded(exact)) == exact
    with pytest.raises(ValueError):
        replace(exact, notes=MemoryNotes(plan_notes=tuple(notes + ["x"])))
    with pytest.raises(ResearchBaseError):
        parse_memory_manifest(encoded(exact) + b" ")
