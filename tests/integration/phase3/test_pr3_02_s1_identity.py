from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import text
from tests.integration.phase3.agent_fixtures import enrollment

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_application_enrollment_and_trusted_subject_resolution(agents):
    command = enrollment(agents)
    result = agents.identity.provision_project_agent(command)
    principal = agents.identity.resolve_agent_subject(command.arguments.subject)
    assert principal.actor_id == result.result_actor_id
    with agents.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT role FROM project_role_assignments WHERE id=:id"),
                {"id": result.result_role_assignment_id},
            ).scalar_one()
            == "RESEARCHER"
        )


@pytest.mark.parametrize(
    "case",
    [
        "owner",
        "operator",
        "subject",
        "credential",
        "project",
        "command",
        "actor",
        "display",
        "expired",
        "self",
        "verifier",
    ],
)
def test_mismatched_proof_denied_without_history(agents, case):
    cmd = enrollment(agents)
    args = cmd.arguments
    proof = args.enrollment_proof
    if case in {"owner", "operator", "project", "command", "actor"}:
        field = {
            "owner": "owner_actor_id",
            "operator": "operator_actor_id",
            "project": "project_id",
            "command": "command_id",
            "actor": "actor_id",
        }[case]
        args = replace(args, enrollment_proof=replace(proof, **{field: new_uuid7()}))
    elif case in {"subject", "credential"}:
        args = replace(
            args,
            enrollment_proof=replace(
                proof,
                **{
                    ("subject_value" if case == "subject" else "subject_credential_id"): "different"
                },
            ),
        )
    elif case == "display":
        args = replace(args, display_name="substituted name")
    elif case == "expired":
        args = replace(
            args,
            enrollment_proof=replace(
                proof,
                verified_at=proof.verified_at - timedelta(days=1),
                expires_at=proof.verified_at,
            ),
        )
    elif case == "self":
        args = replace(args, attestation=replace(args.attestation, operator=agents.owner))
    else:
        agents.verifier.accepted.clear()
    with pytest.raises(ResearchBaseError) as exc:
        agents.identity.provision_project_agent(replace(cmd, arguments=args))
    assert exc.value.code == ErrorCode.SUBJECT_BINDING_UNPROVEN
    with agents.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM actors WHERE actor_type='AGENT'")).scalar_one()
            == 0
        )
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 0


@pytest.mark.parametrize("role", ["OWNER", "APPROVER", "REVIEWER", "VIEWER"])
def test_application_role_ceiling(agents, role):
    from researchbase.application.phase2_identity import AssignProjectRole

    cmd = enrollment(agents)
    agents.service.execute(cmd)
    with pytest.raises(ResearchBaseError) as exc:
        agents.identity.assign_project_role(
            AssignProjectRole(
                agents.owner,
                agents.project,
                cmd.arguments.actor_id,
                role,
                "ceiling test",
                new_uuid7(),
            )
        )
    assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("terminal", ["SUSPENDED", "ENDED"])
def test_original_binding_reactivation_and_revoke(agents, terminal):
    from researchbase.application.phase2_identity import (
        EndProjectMembership,
        ReactivateProjectMembership,
        RevokeActorSubjectBinding,
        SuspendProjectMembership,
    )

    cmd = enrollment(agents)
    result = agents.service.execute(cmd)
    if terminal == "SUSPENDED":
        agents.identity.suspend_project_membership(
            SuspendProjectMembership(
                agents.owner, agents.project, result.result_membership_id, "suspend", new_uuid7()
            )
        )
    else:
        agents.identity.end_project_membership(
            EndProjectMembership(
                agents.owner, agents.project, result.result_membership_id, "end", new_uuid7()
            )
        )
    membership = agents.identity.reactivate_project_membership(
        ReactivateProjectMembership(
            agents.owner, agents.project, cmd.arguments.actor_id, "reactivate", new_uuid7()
        )
    )
    with agents.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT role FROM project_role_assignments WHERE membership_id=:id"),
                {"id": membership},
            ).scalar_one()
            == "RESEARCHER"
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM actor_subject_bindings WHERE actor_id=:id"),
                {"id": cmd.arguments.actor_id},
            ).scalar_one()
            == 1
        )
    agents.identity.revoke_actor_subject_binding(
        RevokeActorSubjectBinding(agents.operator, result.result_binding_id, "revoke", new_uuid7())
    )
    with pytest.raises(ResearchBaseError) as exc:
        agents.identity.resolve_agent_subject(cmd.arguments.subject)
    assert exc.value.code == ErrorCode.SUBJECT_BINDING_UNPROVEN


def test_subject_cannot_substitute_owner_credential(agents):
    cmd = enrollment(agents)
    args = cmd.arguments
    args = replace(
        args,
        subject=replace(args.subject, credential_id=agents.owner.credential_id),
        attestation=replace(args.attestation, subject_credential_id=agents.owner.credential_id),
        enrollment_proof=replace(
            args.enrollment_proof, subject_credential_id=agents.owner.credential_id
        ),
    )
    command = replace(cmd, arguments=args)
    agents.verifier.accepted[command.command_id] = command.material()
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(command)
    assert exc.value.code == ErrorCode.SUBJECT_BINDING_UNPROVEN
