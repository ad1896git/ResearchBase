"""Protect Phase 1 Claim ownership while permitting separate Phase 2 evidence."""

import pytest
from tests.architecture import test_pr12_boundaries as boundary


def _sources():
    return dict.fromkeys(boundary.PHASE1_CLAIM_ROOTS, "")


def test_standalone_phase2_literature_is_authorized():
    sources = _sources()
    sources["researchbase.domain.literature_evidence"] = "class LiteratureEvidence: pass"
    assert boundary._claim_boundary_violations(sources) == []


@pytest.mark.parametrize("root", sorted(boundary.PHASE1_CLAIM_ROOTS))
@pytest.mark.parametrize("indirect", [False, True])
def test_each_claim_root_rejects_literature_ownership(root, indirect):
    sources = _sources()
    if indirect:
        sources[root] = "from researchbase.application import helper"
        sources["researchbase.application.helper"] = "class LiteratureEvidence: pass"
    else:
        sources[root] = "class LiteratureEvidence: pass"
    assert boundary._claim_boundary_violations(sources)


@pytest.mark.parametrize(
    "reference",
    [
        "from researchbase.domain import literature_evidence as evidence",
        "from ..domain import literature_evidence as evidence",
        "import researchbase as rb\nvalue = rb.domain.literature_evidence.LiteratureEvidence",
        (
            "from importlib import import_module as load\n"
            "load('researchbase.domain.literature_evidence')"
        ),
        "__import__('researchbase.domain.literature_evidence')",
        (
            "from importlib import import_module as load\n"
            "load(name='.literature_evidence', package='researchbase.domain')"
        ),
    ],
)
def test_claim_rejects_alias_relative_namespace_and_dynamic_dependencies(reference):
    sources = _sources()
    sources["researchbase.application.commands"] = reference
    sources["researchbase.domain.literature_evidence"] = "class LiteratureEvidence: pass"
    assert boundary._claim_boundary_violations(sources)


@pytest.mark.parametrize("package", ["researchbase", "researchbase.application"])
def test_package_initializers_cannot_bypass_claim_guard(package):
    sources = _sources()
    sources[package] = "class LiteratureEvidence: pass"
    assert boundary._claim_boundary_violations(sources, frozenset({package}))


@pytest.mark.parametrize("forbidden", ["ClaimVersionVersion", "generic EvidenceRepository"])
def test_structural_bans_cover_phase2_too(forbidden):
    sources = _sources()
    sources["researchbase.domain.literature_evidence"] = f"# {forbidden}"
    assert boundary._claim_boundary_violations(sources)


@pytest.mark.parametrize("root", sorted(boundary.PHASE1_CLAIM_ROOTS))
def test_missing_protected_module_fails_closed(root):
    sources = _sources()
    del sources[root]
    with pytest.raises(AssertionError, match="missing protected"):
        boundary._claim_boundary_violations(sources)
