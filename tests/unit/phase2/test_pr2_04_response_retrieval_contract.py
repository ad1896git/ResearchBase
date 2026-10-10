"""Frozen pack §8 and PR204-SUCCESS-01 require success retrieval time."""

from dataclasses import fields

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.domain.literature_search_execution import SearchResponse


@pytest.mark.pr204_requirements('PR204-SUCCESS-01')
def test_neutral_success_response_exposes_required_retrieved_at(pr204_trace: FactRecorder):
    names = [field.name for field in fields(SearchResponse)]
    pr204_trace.record(response_fields=names, required_success_field='retrieved_at')
    assert 'retrieved_at' in names
