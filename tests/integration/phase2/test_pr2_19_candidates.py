"""Offline candidate failure boundaries with committed-state observations."""

from uuid import uuid4

import pytest

from researchbase.application.native_research_strategy import (
    NativeResearchStrategy,
    ResearchStrategyContext,
    ResearchStrategyRequest,
)
from researchbase.application.scientific_rag_provider import (
    FakeScientificRAGCapability,
    SourceLocator,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.pr2_19_support import (
    CORPUS,
    counts,
)
from tests.integration.phase2.pr2_19_support import (
    m3 as _m3,
)
from tests.integration.phase2.pr2_19_support import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_candidate_env as _pr219_candidate_env,
)
from tests.integration.phase2.pr2_19_support import (
    pr219_evidence_env as _pr219_evidence_env,
)
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import context, request, response
from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

pytestmark = pytest.mark.integration


def test_native_strategy_is_candidate_only(pr219_candidate_env):
    env, sources = pr219_candidate_env
    before = counts(env[7])
    strategy = NativeResearchStrategy()
    req = ResearchStrategyRequest("Recall", sources)
    ctx = ResearchStrategyContext(req, lambda: False)
    result = strategy.execute(strategy.prepare_plan(req, ctx), ScriptedRAG(sources[0]), ctx)
    assert result.execution_metadata.query_count == 3
    assert "UNVERIFIED_CANDIDATE" in result.warnings
    assert result.hypothesis_candidates == ()
    assert all(item.source_version_id in sources for item in result.literature_evidence_candidates)
    assert counts(env[7]) == before


@pytest.mark.parametrize(
    "case", ["invented", "out_of_corpus", "absent_paragraph", "substituted_quotation", "valid"]
)
def test_candidate_exact_corpus_and_zero_scientific_delta(pr219_candidate_env, case):
    env, sources = pr219_candidate_env
    service, author, _, project, *_ = env
    before = counts(env[7])
    source = (
        uuid4() if case == "invented" else sources[1] if case == "out_of_corpus" else sources[0]
    )
    candidate = response(
        source,
        locator=SourceLocator(paragraph="99" if case == "absent_paragraph" else "1"),
        excerpt="Fabricated precision" if case == "substituted_quotation" else "improved recall",
    )
    fake = FakeScientificRAGCapability(candidate)
    if case in {"invented", "out_of_corpus"}:
        with pytest.raises(ValueError, match="source"):
            fake.answer(request((sources[0],)), context())
    else:
        result = fake.answer(request(sources), context())
        assert not any(hasattr(fake, name) for name in ("engine", "session", "_factory"))
        item = result.evidence_candidates[0]
        assert item.locator.paragraph is not None
        if case == "valid":
            assert item.excerpt.encode() in CORPUS[0].split(b"\n\n")[0]
        else:
            with pytest.raises(ResearchBaseError) as denied:
                service.create(
                    author,
                    project,
                    item.source_version_id,
                    item.excerpt,
                    uuid4(),
                    paragraph=int(item.locator.paragraph),
                )
            assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert counts(env[7]) == before
    assert before["literature_evidence"] == 0


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_evidence_env = _pr219_evidence_env
