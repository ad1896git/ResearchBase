"""Bounded, in-memory decoding of verified bearing evaluation evidence."""

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass

from researchbase.agent_runtime.domain.bearing_evaluation import (
    Evaluation,
    Group,
    LabeledSample,
    Prediction,
    Protocol,
    evaluate,
)
from researchbase.agent_runtime.domain.research_task import invalid

_LIMIT = 16 * 1024 * 1024
_ROWS = 100000
_SEPARATOR = re.compile(r"[,\r\n]")


@dataclass(frozen=True, slots=True)
class BearingEvidenceHashes:
    labels: str
    baseline_predictions: str
    candidate_predictions: str
    protocol: str

    def __post_init__(self) -> None:
        for value in (
            self.labels,
            self.baseline_predictions,
            self.candidate_predictions,
            self.protocol,
        ):
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                invalid("invalid bearing evidence")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            invalid("invalid bearing evidence")
        result[key] = value
    return result


def _constant(value: str) -> object:
    invalid("invalid bearing evidence")


def _decode(data: bytes) -> str:
    text = data.decode("utf-8", errors="strict")
    if text.startswith("\ufeff"):
        invalid("invalid bearing evidence")
    return text


def _csv_projection(text: str, width: int) -> tuple[str, list[list[str]]]:
    """Keep CSV grammar for strict parsing, with payload held outside the reader.

    Every valid field projects to an empty quoted field, so even a process-wide
    field limit of zero cannot constrain evidence. Quoted payload (including
    doubled quotes and newlines) is retained exactly in the returned fields.
    Invalid quote endings remain invalid in the projection for csv to reject.
    """
    syntax: list[str] = []
    records: list[list[str]] = []
    fields: list[str] = []
    position = 0
    while position < len(text):
        if len(records) > _ROWS or len(fields) >= width:
            invalid("invalid bearing evidence")
        if not fields and text[position] in "\r\n":
            records.append([])
        else:
            if text[position] == '"':
                start = position + 1
                end = text.find('"', start)
                while end != -1 and text[end : end + 2] == '""':
                    end = text.find('"', end + 2)
                if end == -1:
                    return "".join(syntax) + '"', records
                fields.append(text[start:end].replace('""', '"'))
                position = end + 1
            else:
                separator = _SEPARATOR.search(text, position)
                end = len(text) if separator is None else separator.start()
                fields.append(text[position:end])
                position = end
            syntax.append('""')
            if position == len(text):
                records.append(fields)
                break
            if text[position] == ",":
                syntax.append(",")
                position += 1
                if position == len(text):
                    syntax.append('""')
                    records.append([*fields, ""])
                continue
            if text[position] not in "\r\n":
                return "".join(syntax) + "!", records
            records.append(fields)
            fields = []
        terminator = "\r\n" if text[position : position + 2] == "\r\n" else text[position]
        syntax.append(terminator)
        position += len(terminator)
    return "".join(syntax), records


def _table(data: bytes, header: list[str]) -> list[list[str]]:
    syntax, records = _csv_projection(_decode(data), len(header))
    reader = csv.reader(io.StringIO(syntax, newline=""), strict=True)
    rows: list[list[str]] = []
    for index, (shape, row) in enumerate(zip(reader, records, strict=True)):
        if len(shape) != len(header) or len(row) != len(header):
            invalid("invalid bearing evidence")
        if index == 0:
            if row != header:
                invalid("invalid bearing evidence")
            continue
        if len(rows) >= _ROWS:
            invalid("invalid bearing evidence")
        rows.append(row)
    if not rows:
        invalid("invalid bearing evidence")
    return rows


def _protocol(data: bytes) -> Protocol:
    obj: object = json.loads(_decode(data), object_pairs_hook=_pairs, parse_constant=_constant)
    if type(obj) is not dict or set(obj) != {"evaluation_split", "classes", "groups"}:
        invalid("invalid bearing evidence")
    split, classes, groups = obj["evaluation_split"], obj["classes"], obj["groups"]
    if (
        type(split) is not str
        or type(classes) is not list
        or any(type(item) is not str for item in classes)
        or type(groups) is not list
    ):
        invalid("invalid bearing evidence")
    parsed_groups: list[Group] = []
    for group in groups:
        if (
            type(group) is not dict
            or set(group) != {"group_id", "split"}
            or type(group["group_id"]) is not str
            or type(group["split"]) is not str
        ):
            invalid("invalid bearing evidence")
        parsed_groups.append(Group(group["group_id"], group["split"]))
    return Protocol(split, tuple(classes), tuple(parsed_groups))


def evaluate_bytes(
    *,
    labels: bytes,
    baseline_predictions: bytes,
    candidate_predictions: bytes,
    protocol: bytes,
    expected_hashes: BearingEvidenceHashes,
) -> Evaluation:
    """Verify exact bytes before parsing and evaluate aligned observations."""
    inputs = (labels, baseline_predictions, candidate_predictions, protocol)
    if type(expected_hashes) is not BearingEvidenceHashes or any(
        type(value) is not bytes or len(value) > _LIMIT for value in inputs
    ):
        invalid("invalid bearing evidence")
    hashes = (
        expected_hashes.labels,
        expected_hashes.baseline_predictions,
        expected_hashes.candidate_predictions,
        expected_hashes.protocol,
    )
    actual = tuple(hashlib.sha256(data).hexdigest() for data in inputs)
    if actual != hashes:
        invalid("invalid bearing evidence")
    try:
        parsed_protocol = _protocol(protocol)
        samples = tuple(
            LabeledSample(*row)
            for row in _table(labels, ["sample_id", "group_id", "split", "label"])
        )
        header = ["sample_id", "prediction"]
        baseline = tuple(Prediction(*row) for row in _table(baseline_predictions, header))
        candidate = tuple(Prediction(*row) for row in _table(candidate_predictions, header))
        return evaluate(parsed_protocol, samples, baseline, candidate)
    except (UnicodeError, csv.Error, ValueError, RecursionError, OverflowError):
        pass
    invalid("invalid bearing evidence")
