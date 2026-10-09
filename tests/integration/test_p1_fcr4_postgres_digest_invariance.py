"""PostgreSQL-backed P1-FCR4 valid digest invariance checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import select, text
from tests.e2e.support import fresh_fixture, run_workflow
from tests.integration.test_p1_fcr4_ownership_matrix import PERSISTENCE_FAMILIES
from tests.oracles.p1_fcr4_digest_corpus import independent_digest

from researchbase.foundation.frozen_json import thaw_json
from researchbase.persistence.models import EvidenceRelationModel

pytestmark = pytest.mark.integration

MATERIAL_FIELDS = {
    "ResearchQuestionVersion": ("question_text", "scope", "rationale"),
    "HypothesisVersion": ("statement", "expected_direction", "success_criteria", "rationale"),
    "ExperimentSpecVersion": (
        "title",
        "objective",
        "protocol",
        "planned_metrics",
        "seed_policy",
        "analysis_plan",
    ),
    "DatasetSnapshot": ("manifest_hash", "selection_definition"),
    "MetricDefinitionVersion": ("definition", "unit", "aggregation"),
    "Measurement": (
        "run_id",
        "metric_definition_version_id",
        "numeric_value",
        "structured_value",
        "unit",
        "evaluation_scope",
    ),
    "StatisticalResult": ("analysis_type", "result_payload", "analysis_definition"),
    "ClaimVersion": ("statement", "scope", "qualification", "support_set_hash"),
}


def _read_material(family: str, value: object) -> dict[str, object]:
    return {
        field: thaw_json(getattr(value, field))
        if field
        in {
            "scope",
            "success_criteria",
            "protocol",
            "planned_metrics",
            "seed_policy",
            "analysis_plan",
            "selection_definition",
            "definition",
            "structured_value",
            "evaluation_scope",
            "result_payload",
            "analysis_definition",
        }
        else str(getattr(value, field))
        if field in {"run_id", "metric_definition_version_id", "support_set_hash"}
        else getattr(value, field)
        for field in MATERIAL_FIELDS[family]
    }


def _impact_material(value: object) -> dict[str, object]:
    targets = [target.semantic_row() for target in value.targets]  # type: ignore[attr-defined]
    targets.sort(
        key=lambda row: (
            row["target_type"] or "",
            row["target_id"] or "",
            row["target_content_hash"] is not None,
            row["target_content_hash"] or "",
            row["impact_kind"] or "",
        )
    )
    return {
        "project_id": str(value.project_id),  # type: ignore[attr-defined]
        "audit_finding_id": (
            str(value.audit_finding_id)  # type: ignore[attr-defined]
            if value.audit_finding_id is not None  # type: ignore[attr-defined]
            else None
        ),
        "assessment_payload": thaw_json(value.assessment_payload),  # type: ignore[attr-defined]
        "conclusion": value.conclusion.value,  # type: ignore[attr-defined]
        "impact_targets": targets,
    }


def _correction_material(value: object) -> dict[str, object]:
    return {
        "project_id": str(value.project_id),  # type: ignore[attr-defined]
        "target_type": value.target_type.value,  # type: ignore[attr-defined]
        "target_id": str(value.target_id),  # type: ignore[attr-defined]
        "target_content_hash": (
            str(value.target_content_hash)  # type: ignore[attr-defined]
            if value.target_content_hash is not None  # type: ignore[attr-defined]
            else None
        ),
        "correction_type": value.correction_type.value,  # type: ignore[attr-defined]
        "corrected_assertion": thaw_json(value.corrected_assertion),  # type: ignore[attr-defined]
        "reason": value.reason,  # type: ignore[attr-defined]
    }


def test_postgresql_valid_digest_and_orm_roundtrip_corpus(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "p1-fcr4-digest-invariance") as fixture:
        ids = run_workflow(fixture, "application")

        with fixture.engine.connect() as connection:
            assert int(connection.execute(text("SHOW server_version_num")).scalar_one()) == 180006
            database_head = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert database_head == "0018_current_pointer_same_parent_integrity"

        structured: dict[str, tuple[object, str]] = {}
        for family in PERSISTENCE_FAMILIES:
            if family.name in {"ArtifactVersion", "GovernanceStructured"}:
                continue
            value = cast(Any, family.reader(fixture, ids))
            structured[family.name] = (_read_material(family.name, value), str(value.content_hash))

        assessment = fixture.governance_queries.get_impact_assessment(ids.impact_assessment_id)
        correction = fixture.governance_queries.get_correction_record(ids.correction_id)
        assert assessment is not None
        assert correction is not None
        structured["ImpactAssessment"] = (
            _impact_material(assessment),
            str(assessment.content_hash),
        )
        structured["CorrectionRecord"] = (
            _correction_material(correction),
            str(correction.content_hash),
        )

        assert len(structured) == 10
        for material, stored_digest in structured.values():
            assert independent_digest(material) == stored_digest

        artifact = cast(Any, fixture.application.get_artifact_version(ids.artifact_version_id))
        assert str(artifact.content_hash) == hashlib.sha256(b"gsas-source-v1").hexdigest()

        claim = fixture.application.get_claim_version(ids.claim_version_id)
        with fixture.sessions() as session:
            relations = session.execute(
                select(EvidenceRelationModel).where(
                    EvidenceRelationModel.claim_version_id == ids.claim_version_id
                )
            ).scalars()
            rows = []
            for relation in relations:
                source_type = (
                    "measurement" if relation.measurement_id is not None else "statistical_result"
                )
                source_id = relation.measurement_id or relation.statistical_result_id
                relation_type = getattr(relation.relation_type, "value", relation.relation_type)
                rows.append(
                    {
                        "source_type": source_type,
                        "source_id": str(source_id),
                        "relation_type": relation_type,
                        "qualification": relation.qualification,
                    }
                )
        rows.sort(
            key=lambda row: (
                row["source_type"],
                row["source_id"],
                row["relation_type"],
                row["qualification"] is not None,
                row["qualification"] or "",
            )
        )
        assert independent_digest(rows) == str(claim.support_set_hash)

        assert any(target.target_type.value == "run" for target in assessment.targets)
        assert all(
            target.target_content_hash is None
            for target in assessment.targets
            if target.target_type.value == "run"
        )
