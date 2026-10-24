"""Manual literature-evidence Application boundary; no autonomous scientific approval."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NoReturn
from uuid import UUID, uuid4

from researchbase.adapters.source_document import locate, paragraphs, relocate
from researchbase.application.closure import ProvenanceClosureValidator
from researchbase.application.governance_queries import GovernanceQueryService, ValidityState
from researchbase.application.ports import UnitOfWork
from researchbase.application.saved_provenance import reading_saved_seal, saved_dependency
from researchbase.application.source_version import SourceVersionService, _material_from_row
from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.claim import ClaimVersionId
from researchbase.domain.literature_evidence import (
    TRANSITIONS,
    digest,
    evidence_material,
    ref,
    snapshot_material,
    support_material,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisVersionId, ResearchQuestionVersionId
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus

TARGET_COLUMNS = {
    "ClaimVersion": "claim_version_id",
    "HypothesisVersion": "hypothesis_version_id",
    "ResearchQuestionVersion": "research_question_version_id",
}


def _fail(message, code=ErrorCode.VALIDATION_ERROR) -> NoReturn:
    raise ResearchBaseError(code, message)


def _public(value) -> Any:
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_public(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class LiteratureEvidenceService:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        credentials: Any,
        store: ArtifactStore,
        *,
        governance: GovernanceQueryService | None = None,
    ):
        self._factory = factory
        self._credentials = credentials
        self._store = store
        self._validator = ProvenanceClosureValidator(factory)
        self._governance = governance if governance is not None else GovernanceQueryService(factory)

    def _authorize(self, uow, principal, project, roles):
        uow.literature_search_plan.lock_project(project)
        candidates = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            valid = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            valid = False
        for row in candidates:
            if (
                valid
                and row["retired_at"] is None
                and row["actor_type"] == "HUMAN"
                and row["membership_status"] == "ACTIVE"
                and row["role"] in roles
                and row["effective_from"] <= at
                and (row["effective_until"] is None or at < row["effective_until"])
                and row["binding_status"] == "ACTIVE"
                and row["bound_at"] <= at
                and (row["revoked_at"] is None or at < row["revoked_at"])
            ):
                if roles != {
                    "OWNER",
                    "RESEARCHER",
                    "REVIEWER",
                    "VIEWER",
                    "APPROVER",
                } and not uow.literature_search_plan.project_active(project):
                    break
                return at
        _fail("current authenticated project authority unavailable", ErrorCode.FORBIDDEN)

    def _write(self, principal, project, name, request, payload, operation, roles=None):
        if not isinstance(request, UUID):
            _fail("request UUID required")
        input_hash = digest({"type": name, "material_version": 1, **payload})

        def once():
            with self._factory() as uow:
                uow.begin_serializable()
                uow.literature_evidence.prepare_write(name)
                at = self._authorize(uow, principal, project, roles or {"OWNER", "RESEARCHER"})
                uow.source_version.lock_command(
                    principal.deployment_id, project, principal.actor_id, name, request
                )
                repo = uow.literature_evidence
                prior = repo.receipt(principal, project, name, request)
                if prior:
                    if prior["input_hash"] != input_hash:
                        _fail("command replay input conflict")
                    value = self._replay(uow, prior, project)
                    self._authorize(uow, principal, project, roles or {"OWNER", "RESEARCHER"})
                    uow.commit()
                    return _public(value)
                result, result_column, identity = operation(uow, at)
                self._authorize(uow, principal, project, roles or {"OWNER", "RESEARCHER"})
                receipt = {
                    "id": uuid4(),
                    "deployment_id": principal.deployment_id,
                    "project_id": project,
                    "actor_id": principal.actor_id,
                    "command_name": name,
                    "request_id": request,
                    "input_hash": input_hash,
                    result_column: identity,
                    "completed_at": at,
                }
                repo.save_receipt(receipt)
                uow.commit()
                return _public(result)

        return SourceVersionService._retry(once)

    def _replay(self, uow, row, project):
        if row["result_artifact_version_id"]:
            return self._artifact(uow, row["result_artifact_version_id"], project)[0]
        if row["result_snapshot_id"]:
            return self._snapshot(uow, row["result_snapshot_id"], project)
        identity = row["result_evidence_id"]
        if row["result_review_event_id"]:
            # Events are reached through their concrete receipt reference.
            event = uow.literature_evidence.review_event(row["result_review_event_id"])
            identity = event["literature_evidence_id"]
        return self._read(uow, identity, project)

    def _artifact(self, uow, identity, project):
        row = uow.literature_evidence.artifact(identity, project)
        if row is None or row["status"] not in {"FROZEN", "SUPERSEDED"}:
            _fail("exact frozen project document not found", ErrorCode.NOT_FOUND)
        if row["locator"] != "sha256:" + row["content_hash"]:
            _fail("document artifact hash binding mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        try:
            if reading_saved_seal():
                if type(row["byte_size"]) is not int or row["byte_size"] < 0:
                    raise ValueError("invalid retained byte size")
                data = None
            else:
                data = self._store.open(row["locator"])
                if digest_bytes(data) != row["content_hash"] or len(data) != row["byte_size"]:
                    raise ValueError("content digest/size mismatch")
        except (OSError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source artifact missing or altered"
            ) from exc
        metadata = row["metadata"]
        if (
            not isinstance(metadata, dict)
            or metadata.get("access") != "PROJECT_LOCAL"
            or metadata.get("parser") != "manual-document-v1"
            or not metadata.get("retention_basis")
        ):
            _fail(
                "document retention/access policy unavailable",
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            )
        values = paragraphs(data, row["media_type"]) if data is not None else None
        return {
            "artifact_id": row["artifact_id"],
            "artifact_version_id": row["id"],
            "content_hash": row["content_hash"],
            "media_type": row["media_type"],
            "byte_size": row["byte_size"],
            "retention_basis": row["metadata"]["retention_basis"],
            "access": "PROJECT_LOCAL",
            "parser": "manual-document-v1",
        }, values

    def import_document(self, principal, project, content, mime, rights_basis, request):
        if not isinstance(rights_basis, str) or not 1 <= len(rights_basis.strip()) <= 4096:
            _fail("explicit lawful local retention/access basis required")
        paragraphs(content, mime)
        content_hash = digest_bytes(content)

        def operation(uow, at):
            identity = self._store.put_verified(content, content_hash)
            if not self._store.verify(identity):
                _fail("document CAS integrity failure", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
            aid, vid = ArtifactId(uuid4()), ArtifactVersionId(uuid4())
            uow.artifacts.add(
                Artifact(
                    aid,
                    ProjectId(project),
                    "literature_fulltext",
                    "User-supplied source document",
                    rights_basis,
                    ActorId(principal.actor_id),
                    at,
                )
            )
            uow.artifact_versions.add(
                ArtifactVersion(
                    vid,
                    aid,
                    1,
                    VersionStatus.FROZEN,
                    identity,
                    mime,
                    len(content),
                    ContentHash(content_hash),
                    {
                        "retention_basis": rights_basis,
                        "access": "PROJECT_LOCAL",
                        "parser": "manual-document-v1",
                    },
                    ActorId(principal.actor_id),
                    at,
                    at,
                )
            )
            uow.artifacts.update_current_version(aid, vid, 1)
            return self._artifact(uow, vid, project)[0], "result_artifact_version_id", vid

        return self._write(
            principal,
            project,
            "IMPORT_DOCUMENT",
            request,
            {"content_hash": content_hash, "mime": mime, "rights_basis": rights_basis},
            operation,
        )

    def _source(self, uow, identity, project):
        repo = uow.source_version
        row = repo.version(identity, lock=True)
        source = repo.source(row["literature_source_id"], project, lock=True) if row else None
        if source is None or row["status"] not in {"FROZEN", "SUPERSEDED"}:
            _fail("exact frozen source version not found", ErrorCode.NOT_FOUND)
        material = _material_from_row(repo, row)
        if material.digest() != row["content_hash"] or row["hash_scheme"] != "sha256-cjson-v1":
            _fail("source version hash mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        artifact, values = self._artifact(uow, row["fulltext_artifact_version_id"], project)
        current = (
            repo.version(source["current_version_id"]) if source["current_version_id"] else None
        )
        valid = "VALID"
        if row["version_kind"] == "RETRACTED" or (
            current and current["version_kind"] == "RETRACTED"
        ):
            valid = "RETRACTED"
        elif current and current["version_kind"] == "CORRECTED" and current["id"] != row["id"]:
            valid = "STALE"
        return row, artifact, values, valid

    def inspect(self, principal, project, source_version_id, paragraph=1):
        with self._factory() as uow:
            self._authorize(
                uow, principal, project, {"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"}
            )
            row, artifact, values, valid = self._source(uow, source_version_id, project)
            if values is None or type(paragraph) is not int or not 1 <= paragraph <= len(values):
                _fail("paragraph out of range")
            return _public(
                {
                    "source_version": ref("SourceVersion", row),
                    **artifact,
                    "paragraph": paragraph,
                    "paragraph_count": len(values),
                    "text": values[paragraph - 1],
                    "source_validity": valid,
                }
            )

    def create(
        self,
        principal,
        project,
        source_version_id,
        quotation,
        request,
        *,
        paragraph=None,
        start=None,
        end=None,
        artifact_version_id=None,
    ):
        def operation(uow, at):
            source, artifact, values, _ = self._source(uow, source_version_id, project)
            if artifact_version_id is not None and str(artifact_version_id) != str(
                artifact["artifact_version_id"]
            ):
                _fail("document version mismatch")
            locator = locate(values, quotation, paragraph=paragraph, start=start, end=end)
            row = {
                "id": uuid4(),
                "project_id": project,
                "source_version_id": source_version_id,
                "evidence_type": "QUOTATION",
                "locator": locator,
                "extracted_statement": quotation,
                "normalized_assertion": None,
                "extraction_method": "RULE",
                "extraction_execution_ref": None,
                "confidence": "MODERATE",
                "review_status": "UNREVIEWED",
                "created_by": principal.actor_id,
                "created_at": at,
                "hash_scheme": "sha256-cjson-v1",
            }
            row["content_hash"] = digest(evidence_material(row, source))
            uow.literature_evidence.insert_evidence(row)
            return self._read(uow, row["id"], project), "result_evidence_id", row["id"]

        return self._write(
            principal,
            project,
            "CREATE_EVIDENCE",
            request,
            {
                "source_version_id": str(source_version_id),
                "quotation": quotation,
                "paragraph": paragraph,
                "start": start,
                "end": end,
                "artifact_version_id": str(artifact_version_id) if artifact_version_id else None,
            },
            operation,
        )

    def _read(self, uow, identity, project):
        row = uow.literature_evidence.evidence(identity, project)
        if row is None:
            _fail("evidence not found", ErrorCode.NOT_FOUND)
        with saved_dependency():
            return self._read_saved(uow, row, project)

    def _read_saved(self, uow, row, project):
        identity = row["id"]
        source, artifact, values, valid = self._source(uow, row["source_version_id"], project)
        if digest(evidence_material(row, source)) != row["content_hash"] or (
            not reading_saved_seal()
            and relocate(values, row["locator"]) != row["extracted_statement"]
        ):
            _fail(
                "evidence hash or exact passage integrity failure",
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            )
        events = uow.literature_evidence.events(identity)
        status = "UNREVIEWED"
        for event in events:
            if event["prior_status"] != status or event["new_status"] not in TRANSITIONS[status]:
                _fail("evidence review history mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
            status = event["new_status"]
        if row["review_status"] != status:
            _fail("evidence status/history mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        return {
            **artifact,
            **row,
            "document_content_hash": artifact["content_hash"],
            "source_version_hash": source["content_hash"],
            "source_validity": valid,
            "review_events": events,
        }

    def get(self, principal, project, identity):
        with self._factory() as uow:
            self._authorize(
                uow, principal, project, {"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"}
            )
            return _public(self._read(uow, identity, project))

    def review(self, principal, project, evidence_id, status, basis, request):
        if (
            status not in {"VERIFIED", "DISPUTED", "REJECTED"}
            or not isinstance(basis, str)
            or not 1 <= len(basis.strip()) <= 4096
        ):
            _fail("explicit review status and bounded inspection basis required")

        def operation(uow, at):
            evidence = self._read(uow, evidence_id, project)
            if status not in TRANSITIONS[evidence["review_status"]]:
                _fail("invalid evidence review transition", ErrorCode.INVALID_STATE_TRANSITION)
            if status == "VERIFIED" and evidence["created_by"] == principal.actor_id:
                _fail("verification requires an independent human reviewer", ErrorCode.FORBIDDEN)
            event = {
                "id": uuid4(),
                "literature_evidence_id": evidence_id,
                "prior_status": evidence["review_status"],
                "new_status": status,
                "reviewed_by": principal.actor_id,
                "reviewed_at": at,
                "basis": basis,
            }
            uow.literature_evidence.insert_review(event)
            return self._read(uow, evidence_id, project), "result_review_event_id", event["id"]

        return self._write(
            principal,
            project,
            "REVIEW_EVIDENCE",
            request,
            {"evidence_id": str(evidence_id), "status": status, "basis": basis},
            operation,
            {"OWNER", "RESEARCHER", "REVIEWER"},
        )

    def _target(self, uow, kind, identity, project):
        if kind not in TARGET_COLUMNS:
            _fail("unsupported exact scientific target")
        row = uow.literature_evidence.target(kind, identity, project)
        if row is None or row["status"] not in {"FROZEN", "SUPERSEDED"}:
            _fail(
                "frozen same-project scientific target required",
                ErrorCode.FROZEN_REFERENCE_REQUIRED,
            )
        row["current_validity"] = "VALID"
        if kind == "ClaimVersion":
            projection = self._governance.validity_projection_in_uow(
                uow, project, "claim_version", identity
            )
            if projection.state not in {ValidityState.NOT_ASSESSED, ValidityState.UNAFFECTED}:
                row["current_validity"] = (
                    "INVALID" if projection.state == ValidityState.INVALID else "STALE"
                )
            if projection.correction_ids:
                row["current_validity"] = "STALE"
            version = uow.claims.get_version(ClaimVersionId(identity))
            if not self._validator.validate_claim_version_in_uow(
                uow, ClaimVersionId(identity)
            ).complete:
                _fail("Claim closure is invalid", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        elif kind == "HypothesisVersion":
            version = uow.hypotheses.get_version(HypothesisVersionId(identity))
        else:
            version = uow.research_questions.get_version(ResearchQuestionVersionId(identity))
        if version is None or str(version.content_hash) != row["content_hash"]:
            _fail("target material mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        return row

    def snapshot(self, principal, project, kind, target_id, inputs, request):
        if not isinstance(inputs, list) or len(inputs) > 100:
            _fail("bounded relation array required")
        normalized = []
        seen = set()
        for item in inputs:
            if not isinstance(item, dict) or set(item) != {
                "evidence_id",
                "relation_type",
                "qualification",
            }:
                _fail("explicit evidence, relation and qualification required")
            try:
                eid = UUID(str(item["evidence_id"]))
            except ValueError:
                _fail("invalid evidence UUID")
            if eid in seen:
                _fail("duplicate/conflicting relationships require a separate assessment snapshot")
            seen.add(eid)
            qualification = item["qualification"]
            if not isinstance(qualification, str) or not 1 <= len(qualification.strip()) <= 4096:
                _fail("explicit evidentiary relevance/disagreement basis required")
            normalized.append({**item, "evidence_id": str(eid)})

        def operation(uow, at):
            target = self._target(uow, kind, target_id, project)
            if target["current_validity"] != "VALID":
                _fail(
                    "target current scientific validity does not permit new support",
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                )
            edges = []
            for ordinal, item in enumerate(normalized):
                evidence = self._read(uow, UUID(item["evidence_id"]), project)
                if item["relation_type"] == "SUPPORTS":
                    latest = evidence["review_events"][-1] if evidence["review_events"] else None
                    if (
                        evidence["review_status"] != "VERIFIED"
                        or evidence["source_validity"] != "VALID"
                        or latest is None
                        or latest["reviewed_by"] in {evidence["created_by"], principal.actor_id}
                    ):
                        _fail(
                            "SUPPORTS requires independently human-verified valid evidence",
                            ErrorCode.FORBIDDEN,
                        )
                edges.append(
                    {
                        "literature_evidence": ref("LiteratureEvidence", evidence),
                        "relation_type": item["relation_type"],
                        "ordinal": ordinal,
                        "qualification": item["qualification"],
                    }
                )
            binding = digest(support_material(edges))
            previous = uow.literature_evidence.latest(kind, target_id)
            if previous:
                self._snapshot(uow, previous["id"], project)
            row = {
                "id": uuid4(),
                "project_id": project,
                TARGET_COLUMNS[kind]: target_id,
                "snapshot_number": previous["snapshot_number"] + 1 if previous else 1,
                "previous_snapshot_id": previous["id"] if previous else None,
                "literature_support_set_hash": binding,
                "hash_scheme": "sha256-cjson-v1",
                "created_by": principal.actor_id,
                "created_at": at,
                "frozen_at": at,
            }
            row["content_hash"] = digest(snapshot_material(row, ref(kind, target), previous))
            uow.literature_evidence.insert_snapshot(row)
            for edge in edges:
                uow.literature_evidence.insert_relation(
                    {
                        "id": uuid4(),
                        "literature_support_snapshot_id": row["id"],
                        "literature_evidence_id": UUID(edge["literature_evidence"]["id"]),
                        "relation_type": edge["relation_type"],
                        "ordinal": edge["ordinal"],
                        "qualification": edge["qualification"],
                        "created_by": principal.actor_id,
                        "created_at": at,
                    }
                )
            return self._snapshot(uow, row["id"], project), "result_snapshot_id", row["id"]

        return self._write(
            principal,
            project,
            "CREATE_SUPPORT",
            request,
            {"target_type": kind, "target_id": str(target_id), "inputs": normalized},
            operation,
        )

    def _snapshot(self, uow, identity, project):
        if uow.literature_evidence.snapshot(identity, project) is None:
            _fail("literature support snapshot not found", ErrorCode.NOT_FOUND)
        with saved_dependency():
            return self._snapshot_saved(uow, identity, project)

    def _snapshot_saved(self, uow, identity, project):
        # Exact immutable predecessor material is verified iteratively; historical
        # chains must not acquire an arbitrary Python recursion depth limit.
        chain = []
        seen = set()
        current = identity
        while current is not None:
            if current in seen:
                _fail("snapshot predecessor cycle", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
            seen.add(current)
            row = uow.literature_evidence.snapshot(current, project)
            if row is None:
                _fail("literature support snapshot not found", ErrorCode.NOT_FOUND)
            kind = next(key for key, column in TARGET_COLUMNS.items() if row[column] is not None)
            target = self._target(uow, kind, row[TARGET_COLUMNS[kind]], project)
            chain.append((row, kind, target))
            current = row["previous_snapshot_id"]
        previous = None
        for row, kind, target in reversed(chain):
            if previous is not None and (
                previous["snapshot_number"] + 1 != row["snapshot_number"]
                or previous["target"] != ref(kind, target)
            ):
                _fail("snapshot predecessor mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
            previous = self._snapshot_material(uow, row, kind, target, previous, project)
        if previous is None:
            _fail("literature support snapshot not found", ErrorCode.NOT_FOUND)
        return previous

    def _snapshot_material(self, uow, row, kind, target, previous, project):
        relations = uow.literature_evidence.relations(row["id"])
        edges, valid = [], target["current_validity"] == "VALID"
        for relation in relations:
            evidence = self._read(uow, relation["literature_evidence_id"], project)
            edges.append(
                {
                    "literature_evidence": ref("LiteratureEvidence", evidence),
                    **{key: relation[key] for key in ("relation_type", "ordinal", "qualification")},
                }
            )
            if evidence["source_validity"] != "VALID" or evidence["review_status"] in {
                "DISPUTED",
                "REJECTED",
            }:
                valid = False
            if relation["relation_type"] == "SUPPORTS" and (
                evidence["review_status"] != "VERIFIED"
                or not evidence["review_events"]
                or evidence["review_events"][-1]["reviewed_by"]
                in {evidence["created_by"], row["created_by"]}
            ):
                valid = False
        if (
            digest(support_material(edges)) != row["literature_support_set_hash"]
            or digest(snapshot_material(row, ref(kind, target), previous)) != row["content_hash"]
        ):
            _fail("support snapshot hash mismatch", ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
        return {
            **row,
            "target": ref(kind, target),
            "relations": relations,
            "validity": "VALID"
            if valid
            else ("INVALID" if target["current_validity"] == "INVALID" else "STALE"),
        }

    def get_snapshot(self, principal, project, identity):
        with self._factory() as uow:
            self._authorize(
                uow, principal, project, {"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"}
            )
            return _public(self._snapshot(uow, identity, project))


def digest_bytes(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()
