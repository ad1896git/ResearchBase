"""Closed explanation DTOs, exact target matching and fixed response ceilings."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.application.finding_impact import (
    _TARGET_KINDS,
    FindingImpactMatch,
    FindingImpactService,
    GetFindingManuscriptImpactQuery,
    _matches,
)
from researchbase.application.manuscript_validity import (
    AuditNodeRef,
    AuditOccurrence,
    ManuscriptValidityReadback,
    ManuscriptValidityWitness,
    _bounded,
)
from researchbase.domain.governance import (
    AuditFinding,
    AuditFindingId,
    AuditFindingSeverity,
    AuditFindingStatus,
    GovernanceTargetType,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId


def finding(kind=GovernanceTargetType.RUN):
    return AuditFinding(
        AuditFindingId(uuid4()),
        ProjectId(uuid4()),
        "test",
        AuditFindingSeverity.MAJOR,
        "Title",
        "Description",
        kind,
        uuid4(),
        None,
        AuditFindingStatus.OPEN,
        ActorId(uuid4()),
        datetime.now(UTC),
    )


def validity(f, count=1):
    node = AuditNodeRef(_TARGET_KINDS[f.target_type], f.target_id)
    root = AuditNodeRef("ManuscriptVersion", uuid4())
    occurrence = AuditOccurrence("CLAIM", uuid4(), (root, node))
    witness = ManuscriptValidityWitness(node, "INVALID", None, None, None, (occurrence,) * count)
    return ManuscriptValidityReadback(
        f.project_id,
        uuid4(),
        root.id,
        "FROZEN",
        "a" * 64,
        "b" * 64,
        "INVALID",
        (witness,),
        datetime.now(UTC),
    )


@pytest.mark.parametrize(
    "field", ["project_id", "finding_id", "publication_id", "manuscript_version_id"]
)
@pytest.mark.parametrize("bad", ["uuid", None, 1, True, {}, ()])
def test_exact_uuid(field, bad):
    args: dict[str, Any] = {
        name: uuid4()
        for name in ("project_id", "finding_id", "publication_id", "manuscript_version_id")
    }
    args[field] = bad
    with pytest.raises(ResearchBaseError) as error:
        GetFindingManuscriptImpactQuery(**args)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("extra", ["actor_id", "limit", "evaluated_at", "status", "hash"])
def test_closed_frozen(extra):
    ids = [uuid4() for _ in range(4)]
    with pytest.raises(ResearchBaseError):
        GetFindingManuscriptImpactQuery(*ids, **{extra: 1})
    query = GetFindingManuscriptImpactQuery(*ids)
    with pytest.raises(FrozenInstanceError):
        cast(Any, query).finding_id = uuid4()
    assert not hasattr(query, "__dict__")


@pytest.mark.parametrize("bad", [None, {}, (), object()])
def test_wrong_query_never_opens_uow(bad):
    def factory():
        pytest.fail("opened UoW")

    with pytest.raises(ResearchBaseError) as error:
        FindingImpactService(factory, None, None).get_finding_manuscript_impact(
            cast(Any, None), bad
        )
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("kind", list(GovernanceTargetType))
def test_all_eight_exact_mappings(kind):
    f = finding(kind)
    v = validity(f)
    result = _matches(f, (), v)
    assert len(_TARGET_KINDS) == 8
    assert result[0].target == v.witnesses[0].node
    assert result[0].basis == "FINDING_TARGET" and result[0].assessment_id is None
    assert _matches(replace(f, target_id=uuid4()), (), v) == ()
    # Finding status/severity cannot change the owner-derived validity or matching.
    assert _matches(replace(f, status="dismissed", severity="info"), (), v) == result


@pytest.mark.parametrize(
    "basis,assessment", [("FINDING_TARGET", uuid4()), ("ASSESSMENT_TARGET", None)]
)
def test_assessment_id_xor(basis, assessment):
    f = finding()
    match = _matches(f, (), validity(f))[0]
    with pytest.raises(ResearchBaseError):
        FindingImpactMatch(basis, assessment, match.target, match.occurrences)


def test_occurrence_dedup_and_stable_order():
    f = finding()
    v = validity(f)
    first = v.witnesses[0].occurrences[0]
    second = replace(first, placement_id=uuid4())
    v = replace(v, witnesses=(replace(v.witnesses[0], occurrences=(second, first, second)),))
    paths = _matches(f, (), v)[0].occurrences
    assert len(paths) == 2
    assert [str(p.placement_id) for p in paths] == sorted(str(p.placement_id) for p in paths)


@pytest.mark.parametrize("count", [10000, 10001])
def test_ceiling(count):
    if count == 10000:
        _bounded(count)
    else:
        with pytest.raises(ResearchBaseError) as error:
            _bounded(count)
        assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_combined_path_budget():
    f = finding()
    v = validity(f, 10000)
    with pytest.raises(ResearchBaseError, match="ceiling"):
        _matches(f, (), v)
    assert len(_matches(f, (), validity(f, 9999))) == 1


@pytest.mark.parametrize("depth", [256, 257])
def test_depth(depth):
    root = AuditNodeRef("ManuscriptVersion", uuid4())
    if depth == 256:
        assert len(AuditOccurrence(None, None, (root,) * depth).nodes) == depth
    else:
        with pytest.raises(ResearchBaseError):
            AuditOccurrence(None, None, (root,) * depth)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("CONCURRENT_MODIFICATION", 409, 4),
    ],
)
def test_error_maps(name, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    code = ErrorCode(name)
    assert (_STATUS[code], CLI_EXIT_CODES[code]) == (http, cli)


def test_distinct_graph_node_ceiling_and_depth_guards():
    from researchbase.application.manuscript_validity import _Collector

    collector = _Collector(lambda: cast(Any, None), None, None, uuid4())
    # This invokes the actual shared visitor guard, rather than just its helper.
    for _ in range(9999):
        with collector._path("Run", uuid4()):
            pass
    assert len(collector.visited) == 10000
    with pytest.raises(ResearchBaseError, match="ceiling"):
        with collector._path("Run", uuid4()):
            pytest.fail("over-ceiling node admitted")
    collector = _Collector(lambda: cast(Any, None), None, None, uuid4())
    collector.nodes = [collector.root] * 255
    with collector._path("Run", uuid4()):
        assert len(collector.nodes) == 256
        with pytest.raises(ResearchBaseError, match="ceiling"):
            with collector._path("Run", uuid4()):
                pytest.fail("over-depth path admitted")
