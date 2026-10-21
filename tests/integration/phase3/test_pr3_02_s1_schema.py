# ruff: noqa: E501
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration.phase3.agent_fixtures import enrollment, register

from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import new_uuid7


def test_inventory_and_normal_role(agents):
    with agents.engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        assert not conn.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
        ).scalar_one()
        triggers = conn.execute(
            text(
                "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname LIKE "
                "'pr302_%' ORDER BY tgname"
            )
        ).all()
        assert len(triggers) == 14
        assert [(r[0], r[1], r[2]) for r in triggers if r[1]] == [
            ("pr302_receipt_complete_commit", True, True)
        ]
        functions = conn.execute(
            text("SELECT proname,prosecdef,proconfig FROM pg_proc WHERE proname LIKE 'pr302_%'")
        ).all()
        assert len(functions) == 8
        assert all(
            not r[1] and r[2] == ["search_path=pg_catalog, public, pg_temp"] for r in functions
        )
        assert (
            conn.execute(
                text(
                    "SELECT proname FROM pg_trigger JOIN pg_proc ON pg_proc.oid=tgfoid WHERE "
                    "tgname='trg_actor_binding_human'"
                )
            ).scalar_one()
            == "pr302_binding_guard"
        )
        assert (
            conn.execute(
                text(
                    "SELECT proname FROM pg_trigger JOIN pg_proc ON pg_proc.oid=tgfoid WHERE "
                    "tgname='trg_actor_challenge_human'"
                )
            ).scalar_one()
            == "rb_phase2_guard_human_actor"
        )
        indexes = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname LIKE 'pr302_%'")
        ).all()
        assert len(indexes) == 17
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conrelid IN "
                    "('agent_versions'::regclass,'agent_availability'::regclass,'agent_availability_events'::regclass,'agent_command_receipts'::regclass) AND contype='f' AND confdeltype<>'r'"
                )
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE "
                    "conrelid='agent_command_receipts'::regclass AND contype='f' AND condeferrable"
                )
            ).scalar_one()
            == 9
        )


def test_nonascii_sql_python_parity_and_copied_time(agents):
    cmd = enrollment(agents)
    agents.identity.provision_project_agent(cmd)
    reg = register(agents, cmd.arguments.actor_id)
    result = agents.service.execute(reg)
    with agents.engine.connect() as conn:
        row = dict(
            conn.execute(
                text("SELECT * FROM agent_versions WHERE id=:id"),
                {"id": reg.arguments.agent_version_id},
            )
            .mappings()
            .one()
        )
        material = reg.arguments.version_material(agents.project, row["configuration_content_hash"])
        canonical, digest = conn.execute(
            text("SELECT pr216_cjson(CAST(:value AS jsonb)),pr216_hash(CAST(:value AS jsonb))"),
            {"value": json.dumps(material, ensure_ascii=False)},
        ).one()
        assert canonical.encode("utf-8") == canonical_json_bytes(material)
        assert digest == str(sha256_canonical_json(material)) == row["content_hash"]
        assert row["created_at"] == result.recorded_at
        assert row["prompt_template_version"] == "café-研究@1.0.0"
        assert (
            conn.execute(
                text("SELECT occurred_at FROM agent_availability_events WHERE id=:id"),
                {"id": result.result_availability_event_id},
            ).scalar_one()
            == result.recorded_at
        )


@pytest.mark.parametrize(
    "table", ["agent_versions", "agent_command_receipts", "agent_availability_events"]
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_noop_and_delete_immutable(agents, table, operation):
    cmd = enrollment(agents)
    agents.service.execute(cmd)
    result = agents.service.execute(register(agents, cmd.arguments.actor_id))
    identity = {
        "agent_versions": result.result_agent_version_id,
        "agent_command_receipts": result.receipt_id,
        "agent_availability_events": result.result_availability_event_id,
    }[table]
    with agents.engine.begin() as conn:
        with pytest.raises(IntegrityError) as exc:
            conn.execute(
                text(
                    f"{operation} {'FROM ' if operation == 'DELETE' else ''}{table} "
                    + ("SET id=id " if operation == "UPDATE" else "")
                    + "WHERE id=:id"
                ),
                {"id": identity},
            )
        assert (
            getattr(getattr(exc.value.orig, "diag", None), "constraint_name", None)
            == "pr302_immutable"
        )
        conn.rollback()


@pytest.mark.parametrize(
    "case",
    ["actor", "binding", "membership", "role", "version", "late_event", "availability_delete"],
)
def test_unreceipted_or_late_writes_deny(agents, case):
    cmd = enrollment(agents)
    result = agents.service.execute(cmd)
    reg = agents.service.execute(register(agents, cmd.arguments.actor_id))
    with agents.engine.begin() as conn:
        with pytest.raises(IntegrityError):
            if case == "actor":
                conn.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                        "(:id,'AGENT','forged',clock_timestamp())"
                    ),
                    {"id": new_uuid7()},
                )
            elif case == "binding":
                conn.execute(
                    text(
                        "INSERT INTO actor_subject_bindings SELECT "
                        ":id,actor_id,deployment_id,subject_kind,subject_value,status,bound_at,revoked_at,operator_credential_id,subject_credential_id,proof_sha256,proof_record_ref,proof_kind,enrollment_challenge_id,created_at,row_version FROM actor_subject_bindings WHERE id=:old"
                    ),
                    {"id": new_uuid7(), "old": result.result_binding_id},
                )
            elif case == "membership":
                conn.execute(
                    text(
                        "INSERT INTO "
                        "project_memberships(id,project_id,actor_id,status,started_at,created_by,created_at,row_version) VALUES(:id,:p,:a,'ACTIVE',clock_timestamp(),:owner,clock_timestamp(),1)"
                    ),
                    {
                        "id": new_uuid7(),
                        "p": agents.project,
                        "a": cmd.arguments.actor_id,
                        "owner": agents.owner.actor_id,
                    },
                )
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            elif case == "role":
                conn.execute(
                    text("UPDATE project_role_assignments SET role='OWNER' WHERE id=:id"),
                    {"id": result.result_role_assignment_id},
                )
            elif case == "version":
                conn.execute(
                    text(
                        "INSERT INTO agent_versions SELECT "
                        ":id,project_id,actor_id,agent_role,runtime_type,prompt_template_version,model_profile_id,tool_policy_version,capability_set_hash,configuration_artifact_version_id,configuration_content_hash,content_hash,hash_scheme,created_by,created_at FROM agent_versions WHERE id=:old"
                    ),
                    {"id": new_uuid7(), "old": reg.result_agent_version_id},
                )
            elif case == "late_event":
                conn.execute(
                    text(
                        "INSERT INTO agent_availability_events SELECT "
                        ":id,agent_version_id,sequence+1,new_status,'DISABLED',actor_id,occurred_at,reason,receipt_id FROM agent_availability_events WHERE id=:old"
                    ),
                    {"id": new_uuid7(), "old": reg.result_availability_event_id},
                )
            else:
                conn.execute(
                    text("DELETE FROM agent_availability WHERE agent_version_id=:id"),
                    {"id": reg.result_agent_version_id},
                )
        conn.rollback()


def test_db_receipt_time_overrides_input_and_incomplete_root_denied(agents):
    command = enrollment(agents)
    ids = {
        k: new_uuid7()
        for k in (
            "actor",
            "binding",
            "membership",
            "role_assignment",
            "binding_event",
            "membership_event",
            "role_event",
        )
    }
    with agents.factory() as uow:
        uow.begin_agent_command()
        repo = uow.agents
        repo.lock_write(command)
        row = repo.insert(
            "agent_command_receipts",
            {
                "id": new_uuid7(),
                "project_id": agents.project,
                "caller_actor_id": agents.owner.actor_id,
                "command_id": command.command_id,
                "operation": "provision_project_agent",
                "request_hash": command.request_hash(),
                "hash_scheme": "sha256-cjson-v1",
                **{f"result_{k}_id": v for k, v in ids.items()},
                "resulting_revision": 1,
                "recorded_at": datetime(2000, 1, 1, tzinfo=UTC),
            },
        )
        assert row["recorded_at"].year != 2000
        with pytest.raises(IntegrityError) as exc:
            repo.force_constraints()
        assert getattr(exc.value.orig, "sqlstate", None) == "23503"


def test_one_deferred_whole_state_firing_per_command(agents, monkeypatch):
    from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository

    observed = []
    original = SqlAlchemyAgentRepository.force_constraints

    def count(self):
        baseline = self.one(
            "SELECT calls FROM pg_stat_xact_user_functions WHERE funcid='pr302_receipt_complete()'::regprocedure"
        )
        original(self)
        first = self.one(
            "SELECT calls FROM pg_stat_xact_user_functions WHERE funcid='pr302_receipt_complete()'::regprocedure"
        )
        original(self)
        second = self.one(
            "SELECT calls FROM pg_stat_xact_user_functions WHERE funcid='pr302_receipt_complete()'::regprocedure"
        )
        observed.append(
            (
                first["calls"] - (baseline["calls"] if baseline else 0),
                second["calls"] - first["calls"],
            )
        )

    monkeypatch.setattr(SqlAlchemyAgentRepository, "force_constraints", count)
    cmd = enrollment(agents)
    agents.service.execute(cmd)
    agents.service.execute(register(agents, cmd.arguments.actor_id))
    assert observed == [(1, 0), (1, 0)]


@pytest.mark.parametrize(
    "column,value,code",
    [
        ("content_hash", "d" * 64, "PROVENANCE_CLOSURE_VIOLATION"),
        ("configuration_content_hash", "e" * 64, "PROVENANCE_CLOSURE_VIOLATION"),
        ("actor_id", None, "FORBIDDEN"),
        ("configuration_artifact_version_id", None, "REFERENTIAL_INTEGRITY_ERROR"),
    ],
)
def test_independent_db_version_material_guards(agents, monkeypatch, column, value, code):
    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository

    cmd = enrollment(agents)
    agents.service.execute(cmd)
    reg = register(agents, cmd.arguments.actor_id)
    original = SqlAlchemyAgentRepository.insert

    def tampered(self, table, row):
        if table == "agent_versions":
            row = {**row, column: value if value is not None else agents.owner.actor_id}
        return original(self, table, row)

    monkeypatch.setattr(SqlAlchemyAgentRepository, "insert", tampered)
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(reg)
    assert exc.value.code.value == code
