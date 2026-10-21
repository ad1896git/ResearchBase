"""B01 fixtures use existing owning commands and retained real CAS bytes."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from researchbase.application.search_result_resolution import RecordSearchResultResolutionCommand
from researchbase.application.source_identity import (
    RegisterLiteratureSource,
    VerifySourceIdentifier,
)
from researchbase.application.source_version import CreateSourceVersion, TransitionSourceVersion
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
from tests.integration.phase2.test_m2_metadata import provider
from tests.integration.phase2.test_m2_metadata import setup_m2 as _setup_m2

setup_m2 = _setup_m2


@pytest.fixture
def b01_env(setup_m2):
    bundle, principal, project, results, engine, _ = setup_m2
    metadata = bundle.metadata_observations
    provider(metadata, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    observation = metadata.observe(principal, project, results[0], uuid4())
    source = bundle.literature.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project,
            SourceKind.PAPER,
            "Registration display title",
            uuid4(),
            IdentifierType.DOI,
            "10.1234/abc",
        )
    )
    source_id = UUID(str(source["source_id"]))
    identifiers = bundle.literature.list_source_identifiers(principal, project, source_id)
    identifier = UUID(str(identifiers[0]["identifier_id"]))
    basis = UUID(observation["artifact_version_id"])
    bundle.literature.verify_source_identifier(
        VerifySourceIdentifier(
            principal, project, identifier, basis, "Bibliographic DOI verification", uuid4()
        )
    )
    material = SourceVersionMaterial(
        source_id,
        SourceVersionKind.PUBLISHED,
        None,
        None,
        "CRISPR Cas9",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    version = create_version(bundle, principal, project, material)
    command = RecordSearchResultResolutionCommand(
        uuid4(), project, results[0], source_id, version, "Verified DOI and exact version title"
    )
    yield dict(
        bundle=bundle,
        principal=principal,
        project=project,
        results=results,
        engine=engine,
        service=bundle.search_result_resolutions,
        command=command,
        material=material,
        identifier=identifier,
        basis=basis,
    )
    engine.dispose()


def create_version(bundle, principal, project, material, *, freeze=True):
    row = bundle.source_versions.create(CreateSourceVersion(principal, project, material, uuid4()))
    identity = UUID(str(row["source_version_id"]))
    if freeze:
        bundle.source_versions.freeze(
            TransitionSourceVersion(principal, project, identity, uuid4())
        )
    return identity


def record(e, **changes):
    return e["service"].record_search_result_resolution(
        e["principal"], replace(e["command"], **changes)
    )


def count(e, table="search_result_resolutions"):
    with e["engine"].connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def merge_command(e):
    """Prepare approved owning merge commands without changing source history yet."""
    from researchbase.application.source_merge import DecideSourceMerge, ProposeSourceMerge
    from researchbase.application.source_merge_execution import ConsumeSourceMergeProposal
    from researchbase.domain.source_version import FrozenSourceReference

    other = e["bundle"].literature.register_literature_source(
        RegisterLiteratureSource(
            e["principal"], e["project"], SourceKind.PAPER, "Surviving identity", uuid4()
        )
    )
    survivor = UUID(str(other["source_id"]))
    governance = e["bundle"].source_merge
    proposal = governance.propose(
        ProposeSourceMerge(
            e["principal"],
            e["project"],
            e["command"].source_id,
            survivor,
            survivor,
            "Owner-approved duplicate identity handling",
            uuid4(),
            evidence_artifact_ids=(e["basis"],),
        )
    )
    identity = UUID(str(proposal["proposal_id"]))
    governance.decide(DecideSourceMerge(e["principal"], e["project"], identity, "APPROVE", uuid4()))
    with e["engine"].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": e["basis"]}
        ).scalar_one()
    return ConsumeSourceMergeProposal(
        e["principal"],
        e["project"],
        identity,
        str(proposal["proposal_basis_hash"]),
        FrozenSourceReference(e["basis"], digest),
        uuid4(),
    )


def correction_material(e, kind):
    from researchbase.domain.source_version import FrozenSourceReference

    with e["engine"].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM source_versions WHERE id=:id"),
            {"id": e["command"].source_version_id},
        ).scalar_one()
        basis_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": e["basis"]}
        ).scalar_one()
    return replace(
        e["material"],
        version_kind=kind,
        predecessor_source_version=FrozenSourceReference(e["command"].source_version_id, digest),
        correction_basis_artifact=FrozenSourceReference(e["basis"], basis_hash),
    )
