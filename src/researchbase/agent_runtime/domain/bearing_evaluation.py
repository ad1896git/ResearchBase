"""Pure paired classification observations; no inference or activation."""

from dataclasses import dataclass
from fractions import Fraction

from researchbase.agent_runtime.domain.research_task import invalid


def _text(value: object, limit: int | None) -> None:
    if type(value) is not str or not value.strip() or "\x00" in value:
        invalid("invalid bearing evaluation value")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        invalid("invalid bearing evaluation value")
    if limit is not None and size > limit:
        invalid("invalid bearing evaluation value")


@dataclass(frozen=True, slots=True)
class Group:
    group_id: str
    split: str

    def __post_init__(self) -> None:
        _text(self.group_id, 256)
        _text(self.split, None)


@dataclass(frozen=True, slots=True)
class Protocol:
    evaluation_split: str
    classes: tuple[str, ...]
    groups: tuple[Group, ...]

    def __post_init__(self) -> None:
        _text(self.evaluation_split, None)
        if type(self.classes) is not tuple or not 1 <= len(self.classes) <= 64:
            invalid("invalid bearing evaluation protocol")
        for item in self.classes:
            _text(item, 64)
        if len(set(self.classes)) != len(self.classes):
            invalid("invalid bearing evaluation protocol")
        if type(self.groups) is not tuple or not 1 <= len(self.groups) <= 100000:
            invalid("invalid bearing evaluation protocol")
        if any(type(group) is not Group for group in self.groups):
            invalid("invalid bearing evaluation protocol")
        if len({group.group_id for group in self.groups}) != len(self.groups):
            invalid("invalid bearing evaluation protocol")


@dataclass(frozen=True, slots=True)
class LabeledSample:
    sample_id: str
    group_id: str
    split: str
    label: str

    def __post_init__(self) -> None:
        for value in (self.sample_id, self.group_id):
            _text(value, 256)
        _text(self.split, None)
        _text(self.label, 64)


@dataclass(frozen=True, slots=True)
class Prediction:
    sample_id: str
    prediction: str

    def __post_init__(self) -> None:
        _text(self.sample_id, 256)
        _text(self.prediction, 64)


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    label: str
    precision: str | None
    recall: str | None
    f1: str | None


@dataclass(frozen=True, slots=True)
class ModelMetrics:
    correct: int
    accuracy: str
    confusion: tuple[tuple[int, ...], ...]
    per_class: tuple[ClassMetrics, ...]
    macro_precision: str | None
    macro_recall: str | None
    macro_f1: str | None


@dataclass(frozen=True, slots=True)
class Evaluation:
    classes: tuple[str, ...]
    sample_count: int
    baseline: ModelMetrics
    candidate: ModelMetrics
    accuracy_delta: str


def _render(value: Fraction) -> str:
    scaled = abs(value.numerator) * 1000000
    quotient, remainder = divmod(scaled, value.denominator)
    if 2 * remainder > value.denominator or (2 * remainder == value.denominator and quotient % 2):
        quotient += 1
    sign = "-" if value < 0 and quotient else ""
    return f"{sign}{quotient // 1000000}.{quotient % 1000000:06d}"


def _ratio(numerator: int, denominator: int) -> Fraction | None:
    return Fraction(numerator, denominator) if denominator else None


def _model(matrix: list[list[int]], classes: tuple[str, ...], n: int) -> ModelMetrics:
    correct = sum(matrix[i][i] for i in range(len(classes)))
    values: list[tuple[Fraction | None, Fraction | None, Fraction | None]] = []
    for i in range(len(classes)):
        tp = matrix[i][i]
        fp = sum(row[i] for row in matrix) - tp
        fn = sum(matrix[i]) - tp
        values.append((_ratio(tp, tp + fp), _ratio(tp, tp + fn), _ratio(2 * tp, 2 * tp + fp + fn)))

    def render_optional(value: Fraction | None) -> str | None:
        return None if value is None else _render(value)

    def macro(index: int) -> str | None:
        components = [row[index] for row in values]
        if any(value is None for value in components):
            return None
        return _render(
            sum((value for value in components if value is not None), Fraction()) / len(classes)
        )

    return ModelMetrics(
        correct,
        _render(Fraction(correct, n)),
        tuple(tuple(row) for row in matrix),
        tuple(
            ClassMetrics(label, *(render_optional(value) for value in row))
            for label, row in zip(classes, values, strict=True)
        ),
        macro(0),
        macro(1),
        macro(2),
    )


def evaluate(
    protocol: Protocol,
    samples: tuple[LabeledSample, ...],
    baseline: tuple[Prediction, ...],
    candidate: tuple[Prediction, ...],
) -> Evaluation:
    """Compare observations on identical rows, without asserting significance or generalization."""
    if (
        type(protocol) is not Protocol
        or type(samples) is not tuple
        or not 1 <= len(samples) <= 100000
    ):
        invalid("invalid bearing evaluation input")
    if any(type(row) is not LabeledSample for row in samples):
        invalid("invalid bearing evaluation input")
    classes = {label: i for i, label in enumerate(protocol.classes)}
    groups = {group.group_id: group.split for group in protocol.groups}
    expected_groups = {
        group.group_id for group in protocol.groups if group.split == protocol.evaluation_split
    }
    used_groups: set[str] = set()
    truth: dict[str, int] = {}
    for row in samples:
        if (
            row.sample_id in truth
            or row.label not in classes
            or row.split != protocol.evaluation_split
            or groups.get(row.group_id) != row.split
        ):
            invalid("invalid bearing evaluation input")
        truth[row.sample_id] = classes[row.label]
        used_groups.add(row.group_id)
    if used_groups != expected_groups:
        invalid("invalid bearing evaluation input")

    def count(predictions: tuple[Prediction, ...]) -> ModelMetrics:
        if type(predictions) is not tuple or len(predictions) != len(samples):
            invalid("invalid bearing evaluation input")
        matrix = [[0] * len(classes) for _ in classes]
        seen: set[str] = set()
        for row in predictions:
            if (
                type(row) is not Prediction
                or row.sample_id in seen
                or row.sample_id not in truth
                or row.prediction not in classes
            ):
                invalid("invalid bearing evaluation input")
            seen.add(row.sample_id)
            matrix[truth[row.sample_id]][classes[row.prediction]] += 1
        return _model(matrix, protocol.classes, len(samples))

    base = count(baseline)
    cand = count(candidate)
    return Evaluation(
        protocol.classes,
        len(samples),
        base,
        cand,
        _render(Fraction(cand.correct - base.correct, len(samples))),
    )
