"""Regression checks for the historical Phase 1 architecture guard."""

import pytest
from tests.architecture import test_pr14_boundaries as boundary


def test_authorized_decision_does_not_violate_phase1_boundary():
    boundary.test_pr14_has_closed_registry_and_no_generic_graph_or_later_governance()


def _sources():
    return dict.fromkeys(boundary.PHASE1_GOVERNANCE, "")


@pytest.mark.parametrize(
    "reference",
    [
        "import researchbase.application.decision",
        "import researchbase.persistence.decision_repository as repository",
        "from researchbase.domain.decision import DecisionBasisReference as Basis",
        "from researchbase.domain import decision as scientific",
        "from ..domain import decision as scientific",
        "from . import decision as scientific",
        "import researchbase as rb\nservice = rb.application.decision.DecisionService",
        "from importlib import import_module as load\nload('researchbase.domain.decision')",
        "import importlib as loader\nloader.import_module('researchbase.domain.decision')",
        "__import__('researchbase.domain.decision')",
        "from builtins import __import__ as load\nload('researchbase.domain.decision')",
        "from importlib import import_module as load\nload('.decision', 'researchbase.domain')",
    ],
)
def test_forbidden_phase1_decision_dependencies_are_detected(reference):
    sources = _sources()
    sources["researchbase.application.governance"] = reference
    errors = boundary._boundary_violations(sources)
    assert errors
    assert any("researchbase.application.governance -> " in error for error in errors)


@pytest.mark.parametrize("root", sorted(boundary.PHASE1_GOVERNANCE))
def test_each_protected_module_rejects_transitive_reverse_dependencies(root):
    sources = _sources()
    sources[root] = "from researchbase.application import helper"
    sources["researchbase.application.helper"] = "from researchbase.application import ports"
    sources["researchbase.application.ports"] = "import researchbase.application.decision"
    errors = boundary._boundary_violations(sources)
    assert any(
        f"{root} -> researchbase.application.helper -> researchbase.application.ports"
        " -> researchbase.application.decision" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "forbidden",
    [
        "DecisionRecord",
        "ApprovalRequest",
        "ApprovalDecision",
        "ApprovalGrant",
    ],
)
def test_later_governance_objects_remain_forbidden_inside_phase1(forbidden):
    sources = _sources()
    sources["researchbase.domain.governance"] = f"class {forbidden}: pass"
    assert boundary._boundary_violations(sources)


@pytest.mark.parametrize(
    "forbidden",
    [
        "def load_any(): pass",
        "def find_any_target(): pass",
        "import networkx",
        "# graph cache",
    ],
)
def test_generic_graph_bans_still_cover_later_phase_modules(forbidden):
    sources = _sources()
    sources["researchbase.application.decision"] = forbidden
    assert boundary._boundary_violations(sources)


def test_standalone_phase2_and_composition_are_allowed_without_reverse_edge():
    sources = _sources()
    sources["researchbase.domain.decision"] = "payload = {'type': 'DecisionRecord'}"
    sources["researchbase.application.decision"] = "from researchbase.domain import decision"
    sources["researchbase.persistence.uow"] = (
        "from researchbase.persistence import governance_repository, decision_repository"
    )
    sources["researchbase.persistence.decision_repository"] = ""
    assert boundary._boundary_violations(sources) == []


def test_missing_protected_module_is_not_silently_excluded():
    with pytest.raises(AssertionError, match="missing protected"):
        boundary._boundary_violations({})


def test_widening_both_enum_and_registry_cannot_bypass_frozen_targets(monkeypatch):
    from enum import StrEnum

    expanded = StrEnum(
        "Expanded",
        {value.upper(): value for value in (*boundary.PHASE1_TARGETS, "decision_record")},
    )

    class ExpandedRegistry:
        supported_types = frozenset(expanded)

    monkeypatch.setattr(boundary, "GovernanceTargetType", expanded)
    monkeypatch.setattr(boundary, "TargetResolverRegistry", ExpandedRegistry)
    with pytest.raises(AssertionError):
        boundary.test_pr14_has_closed_registry_and_no_generic_graph_or_later_governance()


def test_relative_dependency_inside_package_init_cannot_hide_reverse_edge():
    sources = _sources()
    sources["researchbase.application.governance"] = "import researchbase.bridge"
    sources["researchbase.bridge"] = "from ..domain import decision"
    errors = boundary._boundary_violations(sources, frozenset({"researchbase.bridge"}))
    assert any("researchbase.bridge -> researchbase.domain.decision" in error for error in errors)


def test_importing_package_child_checks_executed_package_initializers():
    sources = _sources()
    sources["researchbase.application.governance"] = "import researchbase.bridge.safe"
    sources["researchbase.bridge.safe"] = ""
    sources["researchbase.bridge"] = "from researchbase.domain import decision"
    errors = boundary._boundary_violations(sources, frozenset({"researchbase.bridge"}))
    assert any("researchbase.bridge -> researchbase.domain.decision" in error for error in errors)


def test_keyword_literal_dynamic_import_is_not_an_escape():
    sources = _sources()
    sources["researchbase.application.governance"] = (
        "import importlib\nimportlib.import_module(name='researchbase.domain.decision')"
    )
    assert boundary._boundary_violations(sources)


def test_alias_cannot_hide_later_object_defined_by_transitive_helper():
    sources = _sources()
    sources["researchbase.application.governance"] = (
        "from researchbase.bridge import Grant\nresult = Grant()"
    )
    sources["researchbase.bridge"] = "class ApprovalGrant: pass\nGrant = ApprovalGrant"
    assert boundary._boundary_violations(sources)


def test_keyword_relative_dynamic_import_checks_literal_package():
    sources = _sources()
    sources["researchbase.application.governance"] = (
        "from importlib import import_module as load\n"
        "load(name='.decision', package='researchbase.domain')"
    )
    assert boundary._boundary_violations(sources)
