from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_pr13_trace_uses_typed_batch_reads_and_request_local_closure_context() -> None:
    query_source = (ROOT / "src/researchbase/application/provenance_queries.py").read_text()
    closure_source = (ROOT / "src/researchbase/application/closure.py").read_text()

    for method in (
        "get_many",
        "list_inputs_for_results",
        "list_dataset_inputs_for_runs",
        "list_artifact_inputs_for_runs",
        "list_by_runs",
    ):
        assert method in query_source

    assert "ClosureEvaluationContext" in closure_source
    assert "run_reports" in closure_source
    assert "run_reports" in query_source


def test_pr13r_does_not_add_graph_or_persistent_cache_schema() -> None:
    source = (ROOT / "src/researchbase/application/provenance_queries.py").read_text()
    forbidden = ("GraphNode", "GraphEdge", "traverse_graph", "closure_cache", "trace_cache")
    assert not any(token in source for token in forbidden)
