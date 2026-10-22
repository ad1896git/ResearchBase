"""Fixed typed input lookups shared by admission and snapshot projections."""

from sqlalchemy import text

INPUT_FAMILIES = {
    "RESEARCH_QUESTION_VERSION": (
        "research_question_version_id",
        "research_question_versions",
        "research_questions",
        "research_question_id",
    ),
    "HYPOTHESIS_VERSION": (
        "hypothesis_version_id",
        "hypothesis_versions",
        "hypotheses",
        "hypothesis_id",
    ),
    "CLAIM_VERSION": ("claim_version_id", "claim_versions", "claims", "claim_id"),
    "SOURCE_VERSION": (
        "source_version_id",
        "source_versions",
        "literature_sources",
        "literature_source_id",
    ),
    "ARTIFACT_VERSION": ("artifact_version_id", "artifact_versions", "artifacts", "artifact_id"),
    "MANUSCRIPT_VERSION": (
        "manuscript_version_id",
        "manuscript_versions",
        "publications",
        "publication_id",
    ),
}


def input_version(session, kind, identity, project):
    _, version, parent, fk = INPUT_FAMILIES[kind]
    scope = (
        (
            "EXISTS(SELECT 1 FROM literature_source_project_links l WHERE "
            "l.literature_source_id=o.id AND l.project_id=:project)"
        )
        if kind == "SOURCE_VERSION"
        else "o.project_id=:project"
    )
    row = (
        session.execute(
            text(
                f"SELECT v.*, {scope} AS scoped FROM {version} v "
                f"JOIN {parent} o ON o.id=v.{fk} WHERE v.id=:id"
            ),
            {"id": identity, "project": project},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None
