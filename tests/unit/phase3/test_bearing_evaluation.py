from dataclasses import FrozenInstanceError
from decimal import localcontext

import pytest

from researchbase.agent_runtime.domain.bearing_evaluation import (
    Group,
    LabeledSample,
    Prediction,
    Protocol,
    evaluate,
)
from researchbase.foundation.errors import ResearchBaseError


def case(
    labels: tuple[str, ...],
    base: tuple[str, ...],
    cand: tuple[str, ...],
    classes: tuple[str, ...] = ("a", "b"),
):
    p = Protocol("eval", classes, (Group("g", "eval"), Group("train", "train")))
    rows = tuple(LabeledSample(str(i), "g", "eval", label) for i, label in enumerate(labels))
    b = tuple(Prediction(str(i), label) for i, label in enumerate(base))
    c = tuple(Prediction(str(i), label) for i, label in enumerate(cand))
    return p, rows, b, c


def test_literal_paired_accuracy_and_confusions():
    args = case(("a", "a", "b", "b"), ("a", "b", "a", "b"), ("a", "a", "a", "b"))
    result = evaluate(*args)
    assert result.baseline.confusion == ((1, 1), (1, 1))
    assert result.candidate.confusion == ((2, 0), (1, 1))
    assert (result.baseline.accuracy, result.candidate.accuracy, result.accuracy_delta) == (
        "0.500000",
        "0.750000",
        "0.250000",
    )
    assert result.candidate.per_class[0].precision == "0.666667"
    assert result.candidate.per_class[0].f1 == "0.800000"
    p, rows, b, c = args
    assert evaluate(p, rows[::-1], b[::-1], c[::-1]) == result


def test_improvement_tie_and_regression():
    args = case(("a", "b"), ("a", "a"), ("a", "b"))
    p, rows, b, c = args
    assert evaluate(*args).accuracy_delta == "0.500000"
    assert evaluate(p, rows, c, c).accuracy_delta == "0.000000"
    assert evaluate(p, rows, c, b).accuracy_delta == "-0.500000"


def test_macro_undefined_and_imbalance():
    defined = evaluate(
        *case(("a", "a", "b", "b"), ("a", "a", "a", "b"), ("a", "a", "a", "b"))
    ).baseline
    # Exact means: (2/3 + 1)/2 = 5/6; (1 + 1/2)/2 = 3/4;
    # (4/5 + 2/3)/2 = 11/15. Averaging rounded components gives wrong last digits.
    assert (defined.macro_precision, defined.macro_recall, defined.macro_f1) == (
        "0.833333",
        "0.750000",
        "0.733333",
    )
    no_precision = evaluate(*case(("a", "a", "a", "b"), ("a",) * 4, ("a",) * 4)).baseline
    # Both classes have support, but b is never predicted: recall mean = 1/2,
    # F1 mean = (6/7 + 0)/2 = 3/7; only macro precision is undefined.
    assert (
        no_precision.macro_precision,
        no_precision.macro_recall,
        no_precision.macro_f1,
    ) == (None, "0.500000", "0.428571")
    no_recall = evaluate(*case(("a",) * 4, ("a", "a", "a", "b"), ("a", "a", "a", "b"))).baseline
    assert (no_recall.macro_precision, no_recall.macro_recall, no_recall.macro_f1) == (
        "0.500000",
        None,
        "0.428571",
    )
    result = evaluate(*case(("a", "a", "a", "b"), ("a",) * 4, ("a",) * 4, ("a", "b", "c")))
    assert result.baseline.confusion == ((3, 0, 0), (1, 0, 0), (0, 0, 0))
    assert result.baseline.per_class[1].precision is None
    assert result.baseline.per_class[1].recall == "0.000000"
    assert result.baseline.per_class[1].f1 == "0.000000"
    assert result.baseline.per_class[2].f1 is None
    assert (
        result.baseline.macro_precision,
        result.baseline.macro_recall,
        result.baseline.macro_f1,
    ) == (None, None, None)


def test_half_even_and_decimal_context_independence():
    labels = ("a",) * 128
    args = case(labels, ("b",) * 128, ("a",) + ("b",) * 127)
    with localcontext() as context:
        context.prec = 2
        assert evaluate(*args).accuracy_delta == "0.007812"
        p, rows, b, c = args
        assert evaluate(p, rows, c, b).accuracy_delta == "-0.007812"
        assert (
            evaluate(*case(labels, ("b",) * 128, ("a",) * 3 + ("b",) * 125)).accuracy_delta
            == "0.023438"
        )


def test_exact_ids_groups_types_and_bounds():
    args = case(("a",), ("a",), ("a",))
    p, rows, b, c = args
    invalid_inputs = [
        (p, (), b, c),
        (p, rows + rows, b + b, c + c),
        (p, rows, (Prediction("extra", "a"),), c),
        (p, rows, (), c),
        (p, list(rows), b, c),
        (p, rows, b, (Prediction("0", "b"), Prediction("0", "a"))),
        (Protocol("eval", ("a", "b"), (Group("g", "eval"), Group("unused", "eval"))), rows, b, c),
        (p, (LabeledSample("0", "train", "eval", "a"),), b, c),
    ]
    for values in invalid_inputs:
        with pytest.raises(ResearchBaseError):
            evaluate(*values)
    for fn in (
        lambda: Protocol("eval", ("a", "a"), (Group("g", "eval"),)),
        lambda: Protocol("eval", (), (Group("g", "eval"),)),
        lambda: Protocol("eval", tuple(str(i) for i in range(65)), (Group("g", "eval"),)),
        lambda: Protocol("eval", ("a",), (Group("g", "eval"), Group("g", "train"))),
        lambda: Prediction("\ud800", "a"),
        lambda: Prediction(" ", "a"),
        lambda: Prediction("a\x00", "a"),
        lambda: Group("é" * 129, "eval"),
        lambda: Protocol("eval", ("é" * 33,), (Group("g", "eval"),)),
    ):
        with pytest.raises(ResearchBaseError):
            fn()
    assert Prediction("é" * 128, "a").sample_id == "é" * 128
    Protocol("eval", tuple(str(i) for i in range(64)), (Group("g", "eval"),))
    many = tuple(LabeledSample(str(i), "g", "eval", "a") for i in range(100000))
    preds = tuple(Prediction(str(i), "a") for i in range(100000))
    assert evaluate(p, many, preds, preds).sample_count == 100000
    with pytest.raises(ResearchBaseError):
        evaluate(p, many + (rows[0],), preds, preds)
    groups = tuple(Group(str(i), "train") for i in range(100000))
    Protocol("eval", ("a",), groups)
    with pytest.raises(ResearchBaseError):
        Protocol("eval", ("a",), groups + (Group("extra", "eval"),))


def test_pure_deterministic_no_activation():
    args = case(("a", "b"), ("a", "a"), ("a", "b"))
    result = evaluate(*args)
    assert result == evaluate(*args)
    with pytest.raises(FrozenInstanceError):
        result.__setattr__("sample_count", 9)
    assert not hasattr(result, "significance")
    assert not hasattr(result, "new_fault")
