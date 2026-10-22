from uuid import UUID

import pytest
from sqlalchemy import text
from tests.integration.phase3.agent_fixtures import enrollment
from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

from researchbase.application.discussion_hypothesis import (
    DiscussionHypothesisCandidate,
    DiscussionHypothesisService,
    PromoteDiscussionHypothesisCommand,
)
from researchbase.application.source_identity import RegisterLiteratureSource, SourceIdentityService
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    PromoteStrategyHypothesisCommand,
    PromoteStrategyQuestionCommand,
    StrategyCandidatePromotionService,
)
from researchbase.domain.source_identity import SourceKind
from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_positive_application_only_agent_g2_and_b03_denial(agents):
    enroll = enrollment(agents)
    agents.identity.provision_project_agent(enroll)
    principal = agents.identity.resolve_agent_subject(enroll.arguments.subject)
    sources = SourceIdentityService(agents.factory, agents.credentials)
    source = sources.register_literature_source(
        RegisterLiteratureSource(
            agents.owner, agents.project, SourceKind.OTHER, "test retained source", new_uuid7()
        )
    )
    source_id = UUID(str(source["source_id"]))
    versions = SourceVersionService(agents.factory, agents.credentials)
    material = SourceVersionMaterial(
        source_id,
        SourceVersionKind.OTHER,
        None,
        None,
        "Retained test source",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    draft = versions.create(
        CreateSourceVersion(agents.owner, agents.project, material, new_uuid7())
    )
    version = UUID(str(draft["source_version_id"]))
    versions.freeze(TransitionSourceVersion(agents.owner, agents.project, version, new_uuid7()))
    service = StrategyCandidatePromotionService(
        agents.factory,
        agents.credentials,
        agents.store,
        ScriptedRAG(version, missing={"What limitations are reported for Recall?"}),
    )
    capture = service.capture_native_strategy(
        principal, CaptureNativeStrategyCommand(new_uuid7(), agents.project, "Recall", (version,))
    )
    question = service.promote_strategy_question(
        principal,
        PromoteStrategyQuestionCommand(
            new_uuid7(), agents.project, capture.id, 0, "Validated open question"
        ),
    )
    hypothesis = service.promote_strategy_hypothesis(
        principal,
        PromoteStrategyHypothesisCommand(
            new_uuid7(),
            agents.project,
            capture.id,
            0,
            "Adapted from retained candidate",
            "Recall may improve",
            question.research_question_id,
        ),
    )
    with agents.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT captured_by FROM strategy_candidate_captures WHERE id=:id"),
                {"id": capture.id},
            ).scalar_one()
            == principal.actor_id
        )
        assert (
            conn.execute(
                text("SELECT created_by FROM hypothesis_versions WHERE id=:id"),
                {"id": hypothesis.hypothesis_version_id},
            ).scalar_one()
            == principal.actor_id
        )
        assert (
            conn.execute(
                text("SELECT created_by FROM research_question_versions WHERE id=:id"),
                {"id": question.research_question_version_id},
            ).scalar_one()
            == principal.actor_id
        )
    discussion = DiscussionHypothesisService(agents.factory, agents.credentials, agents.store)
    candidate = DiscussionHypothesisCandidate(
        new_uuid7(),
        agents.config,
        question.research_question_id,
        "Agent attempt",
        "increase",
        "test rationale",
    )
    with pytest.raises(ResearchBaseError) as exc:
        discussion.promote_discussion_to_hypothesis(
            principal,
            PromoteDiscussionHypothesisCommand(agents.project, new_uuid7(), new_uuid7(), candidate),
        )
    assert exc.value.code == ErrorCode.FORBIDDEN
