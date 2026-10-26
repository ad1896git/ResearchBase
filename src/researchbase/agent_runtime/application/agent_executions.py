"""Create CREATED intents atomically; no work, lifecycle or producer authority."""

from dataclasses import fields
from typing import Any

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommandResult,
    DenyAgentVerifier,
)
from researchbase.agent_runtime.application.agent_versions import authorize_agent_project, fail
from researchbase.agent_runtime.domain.agent_execution import input_material, intent_json
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest, ManifestEntry
from researchbase.agent_runtime.ports.agent_repository import UncertainAgentCommit
from researchbase.agent_runtime.ports.execution_repository import ExecutionUowFactory
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes, sha256_canonical_json
from researchbase.foundation.ids import new_uuid7


class AgentExecutionService:
    def __init__(self, factory: ExecutionUowFactory, credentials, store, *, pins=None):
        self._factory = factory
        self._credentials = credentials
        self._store = store
        self._pins = pins or DenyAgentVerifier()

    def _read(self, repo, command):
        return authorize_agent_project(repo, command.caller, command.project_id, self._credentials)

    def _write(self, repo, command, version):
        at = self._read(repo, command)
        if not repo.project_active(command.project_id):
            fail(ErrorCode.FORBIDDEN, "active project required")
        rows = repo.authority(command.caller, command.project_id)
        actor = command.caller.actor_id
        if not any(
            row["role"]
            in ({"OWNER", "RESEARCHER"} if row["actor_type"] == "HUMAN" else {"RESEARCHER"})
            and row["effective_from"] <= at
            and (row["effective_until"] is None or at < row["effective_until"])
            and row["actor_type"] in {"HUMAN", "AGENT"}
            for row in rows
        ):
            fail(ErrorCode.FORBIDDEN, "intent caller required")
        if not repo.human(actor) and (
            actor != version["actor_id"] or not repo.live_agent(actor, command.project_id)
        ):
            fail(ErrorCode.FORBIDDEN, "exact bound Agent required")
        if not repo.live_agent(version["actor_id"], command.project_id):
            fail(ErrorCode.FORBIDDEN, "live intended Agent required")

    def _version(self, repo, command):
        version = repo.version(command.arguments.agent_version_id)
        if version is not None and version["project_id"] != command.project_id:
            fail(ErrorCode.FORBIDDEN, "intent project mismatch")
        if version is None:
            task = repo.task(command.arguments.research_task_id)
            if task is not None and task["project_id"] != command.project_id:
                fail(ErrorCode.FORBIDDEN, "intent project mismatch")
            fail(ErrorCode.NOT_FOUND, "intent parent absent")
        return version

    def _binding(self, repo, command, version):
        args = command.arguments
        task = repo.task(args.research_task_id)
        if task is not None and task["project_id"] != command.project_id:
            fail(ErrorCode.FORBIDDEN, "intent project mismatch")
        if task is None:
            fail(ErrorCode.NOT_FOUND, "intent parent absent")
        if args.research_task_step_id is not None:
            step = next(
                (s for s in repo.steps(task["id"]) if s["id"] == args.research_task_step_id), None
            )
            if step is None:
                fail(ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "same-task step required")
            if step["status"] != "PENDING":
                fail(ErrorCode.INVALID_STATE_TRANSITION, "pending step required")
        if (
            task["status"] != "PLANNING"
            or task["plan_sealed_at"] is None
            or repo.availability(version["id"])["status"] != "ACTIVE"
        ):
            fail(
                ErrorCode.INVALID_STATE_TRANSITION,
                "sealed planning task and active version required",
            )
        if task["row_version"] != args.expected_task_revision:
            fail(ErrorCode.CONCURRENT_MODIFICATION, "task revision changed")
        return task

    def _frozen(self, repo, identity, project):
        row = repo.configuration(identity)
        if row is None:
            fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "immutable artifact pin unresolved")
        if row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "artifact project mismatch")
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
            fail(ErrorCode.VERSION_NOT_FROZEN, "frozen artifact required")
        return row

    def _preflight(self, command):
        # All external reads finish before opening the write transaction.
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.executions
            self._read(repo, command)
            saved = repo.receipt(command)
            if saved:
                return None
            version = self._version(repo, command)
            self._write(repo, command, version)
            task = self._binding(repo, command, version)
            harness = self._frozen(
                repo, command.arguments.harness_artifact_version_id, command.project_id
            )
            configuration = self._frozen(
                repo, version["configuration_artifact_version_id"], command.project_id
            )
            inputs = repo.inputs(task["id"], command.arguments.research_task_step_id)
            for item in inputs:
                pin = repo.input_version(item.target_kind, item.target_id, command.project_id)
                if pin is None:
                    fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "input pin unresolved")
                if not pin["scoped"]:
                    fail(ErrorCode.FORBIDDEN, "input scope mismatch")
                if pin["status"] not in {"FROZEN", "SUPERSEDED"} or pin["frozen_at"] is None:
                    fail(ErrorCode.VERSION_NOT_FROZEN, "input not frozen")
                if pin["content_hash"] != item.content_hash:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "input pin mismatch")
        for row in (harness, configuration):
            try:
                payload = self._store.open(row["locator"])
            except Exception:
                fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "retained artifact bytes unavailable")
            if (
                len(payload) != row["byte_size"]
                or str(sha256_bytes(payload)) != row["content_hash"]
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained bytes mismatch")
            if row is harness:
                manifest_data = intent_json(payload)
        if type(manifest_data) is not dict or set(manifest_data) != {
            f.name for f in fields(HarnessManifest)
        }:
            fail(ErrorCode.VALIDATION_ERROR, "closed harness manifest required")
        for name in (
            "skills",
            "plugins",
            "adapters",
            "hooks",
            "mcp_capabilities",
            "reference_libraries",
        ):
            try:
                manifest_data[name] = tuple(ManifestEntry(**entry) for entry in manifest_data[name])
            except (TypeError, KeyError):
                fail(ErrorCode.VALIDATION_ERROR, "closed manifest entries required")
        manifest = HarnessManifest(**manifest_data)
        if (
            manifest.config_sha256 != configuration["content_hash"]
            or manifest.model_profile_id != version["model_profile_id"]
            or manifest.prompt_template_version != version["prompt_template_version"]
            or manifest.strategy_id != task["strategy_id"]
            or manifest.strategy_revision != task["strategy_version"]
        ):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "harness binding mismatch")
        try:
            resolved = self._pins.verify(manifest)
        except Exception:
            resolved = False
        if not resolved:
            fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "material executable pins unresolved")
        return (
            harness["content_hash"],
            configuration["content_hash"],
            input_material(
                command.project_id, task["id"], command.arguments.research_task_step_id, inputs
            ),
        )

    def _saved(self, repo, command):
        self._read(repo, command)
        row = repo.receipt(command)
        if row:
            if row["request_hash"] != command.request_hash():
                fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs")
            return repo.result(row, replayed=True)
        occupied = repo.execution(command.arguments.execution_id)
        if occupied:
            if occupied["project_id"] != command.project_id:
                fail(ErrorCode.FORBIDDEN, "intent project mismatch")
            # Reading an intent does not permit replaying another caller's receipt.
            dto = repo.dto(occupied)
            if dto.events[0].actor_id != command.caller.actor_id:
                fail(ErrorCode.FORBIDDEN, "original receipt caller required")
        return None

    def execute(self, command):
        preflight_error = None
        try:
            preflight = self._preflight(command)
        except ResearchBaseError as exc:
            preflight, preflight_error = None, exc
        ids: dict[str, Any] = {}
        for attempt in range(3):
            try:
                return self._once(command, ids, preflight, preflight_error)
            except UncertainAgentCommit:
                result = self.replay(command)
                if result is not None:
                    return result
                raise
            except ResearchBaseError as exc:
                if attempt == 2 or not (exc.details or {}).get("retryable_pr302"):
                    raise
        raise AssertionError("unreachable")

    def _once(self, command, ids, preflight, preflight_error):
        with self._factory() as uow:
            uow.begin_execution_intent()
            repo = uow.executions

            def fresh():
                return self._read(repo, command)

            repo.lock_write(command, fresh)
            saved = self._saved(repo, command)
            if saved is not None:
                return saved
            version = self._version(repo, command)
            self._write(repo, command, version)
            if preflight_error is not None:
                raise preflight_error
            task = self._binding(repo, command, version)
            if preflight is None:
                fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "intent preflight unavailable")
            harness_hash, configuration_hash, inputs = preflight
            harness = self._frozen(
                repo, command.arguments.harness_artifact_version_id, command.project_id
            )
            configuration = self._frozen(
                repo, version["configuration_artifact_version_id"], command.project_id
            )
            material = input_material(
                command.project_id,
                task["id"],
                command.arguments.research_task_step_id,
                repo.inputs(task["id"], command.arguments.research_task_step_id),
            )
            if (
                harness["content_hash"] != harness_hash
                or configuration["content_hash"] != configuration_hash
                or inputs != material
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "preflight pins changed")
            if repo.execution(command.arguments.execution_id):
                fail(ErrorCode.CONCURRENT_MODIFICATION, "intent identity occupied")
            if not ids:
                ids.update(receipt=new_uuid7(), event=new_uuid7())
            receipt_id, event_id = ids["receipt"], ids["event"]
            at = repo.at()
            row: dict[str, Any] = {
                f.name: None for f in fields(AgentCommandResult) if f.name.startswith("result_")
            }
            row.update(
                id=receipt_id,
                project_id=command.project_id,
                caller_actor_id=command.caller.actor_id,
                command_id=command.command_id,
                operation=command.operation,
                request_hash=command.request_hash(),
                hash_scheme="sha256-cjson-v1",
                result_execution_id=command.arguments.execution_id,
                result_execution_event_id=event_id,
                resulting_revision=1,
                recorded_at=at,
            )
            receipt = repo.insert("agent_command_receipts", row)
            fresh()
            at = receipt["recorded_at"]
            intent = {
                "id": command.arguments.execution_id,
                "project_id": command.project_id,
                "research_task_id": task["id"],
                "research_task_step_id": command.arguments.research_task_step_id,
                "task_revision_at_creation": command.arguments.expected_task_revision,
                "agent_version_id": version["id"],
                "actor_id": version["actor_id"],
                "status": "CREATED",
                "revision": 1,
                "created_at": at,
                "input_ref_hash": str(sha256_canonical_json(material)),
                "input_ref_hash_scheme": "sha256-cjson-v1",
                "harness_artifact_version_id": command.arguments.harness_artifact_version_id,
                "harness_content_hash": harness_hash,
                "harness_hash_scheme": "sha256-bytes-v1",
            }
            repo.insert("agent_execution_instances", intent)
            fresh()
            repo.insert(
                "agent_execution_events",
                {
                    "id": event_id,
                    "execution_id": intent["id"],
                    "sequence": 1,
                    "prior_status": None,
                    "new_status": "CREATED",
                    "actor_id": command.caller.actor_id,
                    "occurred_at": at,
                    "reason": "Execution intent created.",
                    "receipt_id": receipt_id,
                },
            )
            fresh()
            repo.force_constraints()
            self._write(repo, command, version)
            uow.commit()
            return repo.result(receipt, replayed=False)

    def replay(self, command):
        with self._factory() as uow:
            uow.begin_formal_read()
            return self._saved(uow.executions, command)

    def get_agent_execution(self, query):
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.executions
            self._read(repo, query)
            row = repo.execution(query.execution_id)
            if row is None:
                fail(ErrorCode.NOT_FOUND, "intent absent")
            if row["project_id"] != query.project_id:
                fail(ErrorCode.FORBIDDEN, "intent project mismatch")
            return repo.dto(row)

    def list_task_executions(self, query):
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.executions
            self._read(repo, query)
            task = repo.task(query.research_task_id)
            if task is None:
                fail(ErrorCode.NOT_FOUND, "task absent")
            if task["project_id"] != query.project_id:
                fail(ErrorCode.FORBIDDEN, "task project mismatch")
            return repo.page(query)
