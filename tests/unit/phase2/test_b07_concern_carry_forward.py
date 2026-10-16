"""Exact correspondence matrix independently constructs result witnesses."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.domain.revision_action import (
    RevisionBasis,
    VersionLineage,
    validate_concern_correspondence,
)


@pytest.mark.parametrize(
    "kind",
    [
        "CLAIM_CHANGE",
        "CONCLUSION_CHANGE",
        "NEW_EXPERIMENT",
        "ANALYSIS_CHANGE",
        "SOURCE_CHANGE",
        "NO_CHANGE",
    ],
)
@pytest.mark.parametrize("valid", [False, True])
def test_every_exact_result_witness(kind, valid):
    owner, oldid, newid, run, stat, source, specid = [uuid4() for _ in range(7)]
    old = VersionLineage(oldid, owner, 1)
    new = VersionLineage(newid, owner, 2)
    spec = VersionLineage(specid, uuid4(), 1)
    before = RevisionBasis((old,), old if kind == "CONCLUSION_CHANGE" else None)
    target = RevisionBasis(
        (new,),
        new if kind == "CONCLUSION_CHANGE" else None,
        experiments=((run, spec),),
        statistics=frozenset({stat}),
        sources=frozenset({source}),
    )
    action = dict(
        action_type=kind,
        result_claim_version_id=newid,
        result_scientific_conclusion_version_id=newid,
        result_run_id=run,
        result_experiment_spec_version_id=specid,
        result_statistical_result_id=stat,
        result_source_version_id=source,
    )
    targetid = oldid if kind == "NO_CHANGE" else newid
    if not valid:
        if kind in {"CLAIM_CHANGE", "CONCLUSION_CHANGE", "NO_CHANGE"}:
            targetid = uuid4()
        elif kind == "NEW_EXPERIMENT":
            target = replace(target, experiments=((run, replace(spec, id=uuid4())),))
        elif kind == "ANALYSIS_CHANGE":
            target = replace(target, statistics=frozenset({uuid4()}))
        else:
            target = replace(target, sources=frozenset({uuid4()}))
    if valid:
        validate_concern_correspondence(action, before, target, target_id=targetid, old_id=oldid)
    else:
        with pytest.raises(ValueError):
            validate_concern_correspondence(
                action, before, target, target_id=targetid, old_id=oldid
            )


@pytest.mark.parametrize("kind", ["NEW_EXPERIMENT", "ANALYSIS_CHANGE", "SOURCE_CHANGE"])
def test_same_project_unrelated_identity_never_corresponds(kind):
    old = VersionLineage(uuid4(), uuid4(), 1)
    new = VersionLineage(uuid4(), uuid4(), 2)
    run, stat, source = uuid4(), uuid4(), uuid4()
    action = dict(
        action_type=kind,
        result_run_id=run,
        result_experiment_spec_version_id=new.id,
        result_statistical_result_id=stat,
        result_source_version_id=source,
    )
    target = RevisionBasis(
        (new,), experiments=((run, new),), statistics=frozenset({stat}), sources=frozenset({source})
    )
    with pytest.raises(ValueError):
        validate_concern_correspondence(
            action, RevisionBasis((old,)), target, target_id=new.id, old_id=old.id
        )
