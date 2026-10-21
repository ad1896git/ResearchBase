from datetime import date
from typing import cast
from uuid import UUID

import pytest

from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial


def test_source_version_material_matches_contract_golden_vector() -> None:
    material = SourceVersionMaterial(
        literature_source_id=UUID("00000000-0000-0000-0000-000000000001"),
        version_kind=SourceVersionKind.PUBLISHED,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Café study",
        abstract=None,
        authors=({"name": "Ana Lee", "orcid": None},),
        publication_date=date(2024, 1, 2),
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=None,
    )

    assert material.digest() == "dc89646783c513cbe656a285836705bc8986e871715a837597309024eda2b8ca"


def test_source_version_material_rejects_open_metadata_schema() -> None:
    with pytest.raises(ValueError, match="metadata"):
        SourceVersionMaterial(
            literature_source_id=UUID("00000000-0000-0000-0000-000000000001"),
            version_kind=SourceVersionKind.PUBLISHED,
            predecessor_source_version=None,
            correction_basis_artifact=None,
            title="Study",
            abstract=None,
            authors=({"name": "Ana Lee", "orcid": None},),
            publication_date=None,
            venue=None,
            external_version_label=None,
            fulltext_artifact=None,
            metadata=cast(dict[str, str | None], {"provider_payload": {"unexpected": True}}),
        )


def test_source_version_material_accepts_its_immutable_metadata_snapshot() -> None:
    fields = {
        "journal_identifier": "issn:1234-5678",
        "volume": "4",
        "issue": None,
        "pages": "1-9",
        "license_label": None,
        "public_repository_label": "Archive",
    }
    material = SourceVersionMaterial(
        literature_source_id=UUID("00000000-0000-0000-0000-000000000001"),
        version_kind=SourceVersionKind.PUBLISHED,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title="Study",
        abstract=None,
        authors=({"name": "Ana Lee", "orcid": None},),
        publication_date=None,
        venue=None,
        external_version_label=None,
        fulltext_artifact=None,
        metadata=fields,
    )
    revised = SourceVersionMaterial(
        literature_source_id=material.literature_source_id,
        version_kind=material.version_kind,
        predecessor_source_version=None,
        correction_basis_artifact=None,
        title=material.title,
        abstract=material.abstract,
        authors=material.authors,
        publication_date=material.publication_date,
        venue=material.venue,
        external_version_label=material.external_version_label,
        fulltext_artifact=material.fulltext_artifact,
        metadata=material.metadata,
    )
    assert revised.digest() == material.digest()
