import csv
import hashlib
import io
import json
from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from researchbase.agent_runtime.application.bearing_evidence import (
    BearingEvidenceHashes,
    evaluate_bytes,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

LABELS = b"sample_id,group_id,split,label\n1,g,eval,a\n2,g,eval,a\n3,g,eval,b\n4,g,eval,b\n"
BASE = b"sample_id,prediction\n1,a\n2,b\n3,a\n4,b\n"
CAND = b"sample_id,prediction\n1,a\n2,a\n3,a\n4,b\n"
PROTOCOL = (
    b'{"evaluation_split":"eval","classes":["a","b"],"groups":[{"group_id":"g","split":"eval"}]}'
)


def run(labels=LABELS, baseline_predictions=BASE, candidate_predictions=CAND, protocol=PROTOCOL):
    values = (labels, baseline_predictions, candidate_predictions, protocol)
    hashes = BearingEvidenceHashes(*(hashlib.sha256(x).hexdigest() for x in values))
    return evaluate_bytes(
        labels=labels,
        baseline_predictions=baseline_predictions,
        candidate_predictions=candidate_predictions,
        protocol=protocol,
        expected_hashes=hashes,
    )


def reject(**kwargs):
    with pytest.raises(ResearchBaseError) as exc:
        run(**kwargs)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert "secret" not in str(exc.value)


def test_literal_metrics_and_independent_permutations():
    result = run()
    assert result.baseline.confusion == ((1, 1), (1, 1))
    assert result.candidate.confusion == ((2, 0), (1, 1))
    assert (result.baseline.accuracy, result.candidate.accuracy, result.accuracy_delta) == (
        "0.500000",
        "0.750000",
        "0.250000",
    )
    assert (
        result.candidate.macro_precision,
        result.candidate.macro_recall,
        result.candidate.macro_f1,
    ) == ("0.833333", "0.750000", "0.733333")
    assert (
        run(
            labels=b"sample_id,group_id,split,label\n4,g,eval,b\n2,g,eval,a\n1,g,eval,a\n3,g,eval,b\n",
            baseline_predictions=b"sample_id,prediction\n3,a\n1,a\n4,b\n2,b\n",
            candidate_predictions=b"sample_id,prediction\n2,a\n4,b\n3,a\n1,a\n",
        )
        == result
    )


def test_hash_value_and_validation_before_parsing():
    hashes = BearingEvidenceHashes(
        *(hashlib.sha256(x).hexdigest() for x in (LABELS, BASE, CAND, PROTOCOL))
    )
    with pytest.raises(FrozenInstanceError):
        hashes.__setattr__("labels", "a" * 64)
    for value in ("A" * 64, "a" * 63, 1):
        with pytest.raises(ResearchBaseError):
            replace(hashes, labels=value)
    for updates in (
        {"labels": hashes.baseline_predictions},
        {"baseline_predictions": hashes.candidate_predictions},
    ):
        with pytest.raises(ResearchBaseError):
            evaluate_bytes(
                labels=LABELS,
                baseline_predictions=BASE,
                candidate_predictions=CAND,
                protocol=PROTOCOL,
                expected_hashes=replace(hashes, **updates),
            )
    for values in (
        {"labels": bytearray(LABELS)},
        {"protocol": b" " * (16 * 1024 * 1024 + 1)},
        {"expected_hashes": object()},
    ):
        args: Any = dict(
            labels=LABELS,
            baseline_predictions=BASE,
            candidate_predictions=CAND,
            protocol=PROTOCOL,
            expected_hashes=hashes,
        )
        args.update(values)
        with pytest.raises(ResearchBaseError):
            evaluate_bytes(**args)
    assert run(protocol=PROTOCOL + b" " * (16 * 1024 * 1024 - len(PROTOCOL))).sample_count == 4


@pytest.mark.parametrize(
    "protocol",
    [
        b"\xff",
        b"\xef\xbb\xbf{}",
        b'{"evaluation_split":"eval","evaluation_split":"eval","classes":[],"groups":[]}',
        b'{"evaluation_split":"eval","classes":["a"],"groups":[{"group_id":"g","group_id":"g","split":"eval"}]}',
        PROTOCOL[:-1] + b',"version":1}',
        PROTOCOL.replace(b'"split":"eval"', b'"split":"eval","extra":0'),
        b'{"evaluation_split":NaN,"classes":[],"groups":[]}',
        b'{"evaluation_split":Infinity,"classes":[],"groups":[]}',
        b"[" * 2000 + b"]" * 2000,
        b'{"evaluation_split":1,"classes":[],"groups":[]}',
        b"{",
    ],
)
def test_invalid_protocol(protocol):
    reject(protocol=protocol)


@pytest.mark.parametrize(
    "labels",
    [
        b"\xff",
        b"\xef\xbb\xbf" + LABELS,
        LABELS.replace(b"sample_id,group_id", b"group_id,sample_id"),
        LABELS.replace(b"1,g,eval,a", b"1,g,eval"),
        LABELS + b"\n",
        LABELS.replace(b"1,g,eval,a", b'"1,g,eval,a'),
        b"sample_id,group_id,split,label\n",
        LABELS.replace(b"2,g,eval,a", b"1,g,eval,a"),
        LABELS.replace(b"g,eval,a", b"other,eval,a"),
    ],
)
def test_invalid_csv_and_labels(labels):
    reject(labels=labels)


@pytest.mark.parametrize(
    "predictions",
    [
        b"sample_id,prediction\n",
        BASE + b"5,a\n",
        b"sample_id,prediction\n1,a\n1,b\n3,a\n4,b\n",
        BASE.replace(b"4,b", b"5,b"),
        BASE.replace(b"prediction", b"prediction,extra"),
    ],
)
def test_invalid_predictions(predictions):
    reject(baseline_predictions=predictions)


def test_unicode_exact_bytes_and_ids():
    labels = LABELS.replace(b"1,g", "é,g".encode())
    baseline = BASE.replace(b"1,a", "é,a".encode())
    candidate = CAND.replace(b"1,a", "é,a".encode())
    assert (
        run(
            labels=labels, baseline_predictions=baseline, candidate_predictions=candidate
        ).sample_count
        == 4
    )
    reject(
        labels=labels,
        baseline_predictions=baseline.replace("é".encode(), "e\u0301".encode()),
        candidate_predictions=candidate,
    )


def test_row_boundaries():
    labels = b"sample_id,group_id,split,label\n" + b"".join(
        f"{i},g,eval,a\n".encode() for i in range(100001)
    )
    preds = b"sample_id,prediction\n" + b"".join(f"{i},a\n".encode() for i in range(100001))
    labels_100k = labels[: labels.rfind(b"100000,")]
    preds_100k = preds[: preds.rfind(b"100000,")]
    assert (
        run(
            labels=labels_100k, baseline_predictions=preds_100k, candidate_predictions=preds_100k
        ).sample_count
        == 100000
    )
    reject(labels=labels, baseline_predictions=preds_100k, candidate_predictions=preds_100k)
    reject(labels=labels_100k, baseline_predictions=preds, candidate_predictions=preds_100k)


@pytest.mark.parametrize("limit", [0, 1, 131072])
def test_long_split_independent_of_csv_field_limit(limit):
    # Include quoted CSV payload, escaped quotes, Unicode, and embedded CRLF.
    split = "s" * 140000 + ',"é\r\nend'
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("sample_id", "group_id", "split", "label"))
    writer.writerow(("1", "g", split, "a"))
    protocol = json.dumps(
        {
            "evaluation_split": split,
            "classes": ["a"],
            "groups": [{"group_id": "g", "split": split}],
        },
        ensure_ascii=False,
    ).encode()
    predictions = b"sample_id,prediction\n1,a\n"
    previous = csv.field_size_limit(limit)
    try:
        result = run(
            labels=stream.getvalue().encode(),
            baseline_predictions=predictions,
            candidate_predictions=predictions,
            protocol=protocol,
        )
        assert csv.field_size_limit() == limit
    finally:
        csv.field_size_limit(previous)
    assert result.sample_count == 1
    assert result.baseline.confusion == ((1,),)
    assert result.baseline.accuracy == "1.000000"
    assert result.candidate.accuracy == "1.000000"
    assert result.accuracy_delta == "0.000000"


@pytest.mark.parametrize(
    "record",
    [
        b'"1",g,"eval",a\r\n',
        b"1,g,eval,a",
        b"1,g,eval,a\r",
        b"1,g,eval,a\n",
    ],
)
def test_csv_record_terminators_and_quotes(record):
    assert (
        run(
            labels=b"sample_id,group_id,split,label\n" + record,
            baseline_predictions=b"sample_id,prediction\n1,a",
            candidate_predictions=b"sample_id,prediction\n1,a",
        ).sample_count
        == 1
    )


@pytest.mark.parametrize(
    "record", [b'"1"x,g,eval,a\n', b'"1,g,eval,a', b"1,g,eval,a,", b"1,g,eval,a\r\n\r\n"]
)
def test_csv_invalid_quote_suffix_and_trailing_columns(record):
    reject(labels=b"sample_id,group_id,split,label\n" + record)
