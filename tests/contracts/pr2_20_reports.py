"""Deterministic engineering inventories and conservative six-report renderer."""

from __future__ import annotations

import ast
import json
import subprocess
import tomllib
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, cast

from tests.contracts.pr2_20_evidence import (
    AQ_S3,
    B28_DISPOSITION,
    EXIT_DEFERRALS,
    LINUX_DISPOSITION,
    SUBJECT_PREFIX,
    AdapterInventoryEntry,
    ExitCriterionEvidence,
    Mode,
    canonical_bytes,
    digest_bytes,
    subject_digest,
    to_bytes,
)

ROOT = Path(__file__).resolve().parents[2]
REPORT_NAMES = (
    "reference_system_inventory.md",
    "adapter_compatibility_report.md",
    "migration_inventory_phase2.md",
    "literature_trace_demo.md",
    "publication_trace_demo.md",
    "phase2_exit_report.md",
)
# Generated outputs are excluded to avoid a self-referential digest. All authored
# code/tests/docs (including this implementation) are included, tracked or untracked.
GENERATED = tuple("docs/phase2/" + name for name in (*REPORT_NAMES, "pr2_20_verification.md"))


def generated(path: str) -> bool:
    return path.startswith("pr_evidence/pr2-20/") or path in GENERATED


def subject(root: Path = ROOT) -> tuple[str, str, str]:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    tracked = subprocess.check_output(
        [
            "git",
            "diff",
            "HEAD",
            "--binary",
            "--",
            ".",
            ":!pr_evidence/pr2-20",
            *(":!" + path for path in GENERATED),
        ],
        cwd=root,
    )
    paths = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root
    )
    untracked = []
    for raw in sorted(part for part in paths.split(b"\0") if part):
        path = raw.decode()
        if not generated(path):
            untracked.append([path, digest_bytes((root / path).read_bytes())])
    dirty = digest_bytes(tracked + b"\0" + canonical_bytes(untracked))
    return revision, dirty, subject_digest(revision, dirty)


def context(root: Path = ROOT) -> dict[str, Any]:
    revision, dirty, _ = subject(root)
    return dict(
        schema_version=1,
        subject_revision=revision,
        dirty_diff_sha256=dirty,
        status="BLOCKED",
        reason="Owning acceptance and owner dispositions not attached",
        evidence_refs=(),
    )


def b28_context(root: Path, deferred: bool) -> dict[str, Any]:
    values = context(root)
    if deferred:
        values.update(status="DEFERRED", reason="Owner-approved B28 deferral: " + B28_DISPOSITION)
    return values


def migration_inventory(root: Path = ROOT) -> list[dict[str, Any]]:
    result = []
    for path in sorted((root / "migrations/versions").glob("*.py")):
        tree = ast.parse(path.read_bytes())
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                        values[target.id] = (
                            ast.literal_eval(node.value) if node.value is not None else None
                        )
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in {"revision", "down_revision"}:
                    values[node.target.id] = (
                        ast.literal_eval(node.value) if node.value is not None else None
                    )
        if "revision" in values:
            result.append(
                dict(
                    path=path.relative_to(root).as_posix(),
                    sha256=digest_bytes(path.read_bytes()),
                    **values,
                )
            )
    return result


def migration_inventory_table(migrations: list[dict[str, Any]]) -> str:
    """Render every discovered revision, including parallel successors of B31."""
    return "| Revision | Predecessor | SHA256 |\n| --- | --- | --- |\n" + "".join(
        f"| {item['revision']} | {item['down_revision']} | {item['sha256']} |\n"
        for item in migrations
    )


def adapter_inventory(root: Path = ROOT) -> tuple[AdapterInventoryEntry, ...]:
    entries = (
        (
            "literature-search",
            "openalex",
            "works-v1",
            "src/researchbase/adapters/openalex.py",
            "https://docs.openalex.org/",
            "REST-unversioned",
            "TEST_ONLY",
        ),
        (
            "identifier-verification",
            "crossref",
            "doi-v1",
            "src/researchbase/adapters/crossref.py",
            "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
            "REST-unversioned",
            "TEST_ONLY",
        ),
        (
            "research-strategy",
            "native-storm-like",
            "candidate-v1",
            "src/researchbase/application/native_research_strategy.py",
            "local-source",
            None,
            "TEST_ONLY",
        ),
        (
            "scientific-rag",
            "fake-scientific-rag",
            "1",
            "src/researchbase/application/scientific_rag_provider.py",
            "offline-fake",
            "test-only",
            "TEST_ONLY",
        ),
        (
            "scientific-rag",
            "paperqa2",
            "unselected",
            "src/researchbase/application/scientific_rag_provider.py",
            "https://github.com/Future-House/paper-qa",
            None,
            "DEFERRED",
        ),
        (
            "research-strategy",
            "official-storm",
            "unselected",
            "src/researchbase/application/native_research_strategy.py",
            "https://github.com/stanford-oval/storm",
            None,
            "METHOD_REFERENCE",
        ),
    )
    lock = digest_bytes((root / "uv.lock").read_bytes())
    return tuple(
        AdapterInventoryEntry(
            **b28_context(root, adapter == "paperqa2"),
            capability_id=capability,
            adapter_id=adapter,
            mapping_version=mapping,
            upstream_source=upstream,
            owner="Repository owner",
            local_source_sha256=digest_bytes((root / path).read_bytes()),
            upstream_revision=None,
            package_version=None,
            api_profile=api,
            model_id=None,
            corpus_format=None,
            index_format=None,
            material_provenance_path=path,
            reviewer=None,
            lock_sha256=lock,
            license_sha256=None,
            mode=cast(Mode, mode),
            reviewed_at=None,
            compatibility_nodes=(),
            unresolved_items=(
                "Authoritative resolved-revision license and dated advisory review unavailable",
                "Offline/source inventory is not live provider or PaperQA2 acceptance",
            ),
        )
        for capability, adapter, mapping, path, upstream, api, mode in entries
    )


def exit_rows(
    root: Path = ROOT, *, acceptance_directory: Path | None = None
) -> tuple[ExitCriterionEvidence, ...]:
    rows = tuple(
        ExitCriterionEvidence(
            **b28_context(root, criterion == "PaperQA2 Adapter"),
            criterion=criterion,
            corrected_term={
                "LiteratureSearchPlan/Run provenance": "LiteratureSearchExecution",
                "SubmissionVersion package freeze": "PreparedSubmissionVersion",
            }.get(criterion),
            acceptance_revision=None,
            owning_prs=EXIT_OWNERS[criterion],
            contract_refs=(B31_CONTRACT, "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"),
            test_nodes=EXIT_NODES.get(criterion, ()),
            commands=(),
            exit_codes=(),
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            finding_refs=(),
            disposition_refs=(B28_DISPOSITION,) if criterion == "PaperQA2 Adapter" else (),
        )
        for criterion in EXIT_CRITERIA
    )

    if acceptance_directory is None:
        return rows
    loaded = []
    for number, row in enumerate(rows):
        if row.status == "DEFERRED":
            loaded.append(row)
            continue
        path = acceptance_directory / f"owning-{number + 1:02d}.json"
        try:
            data = json.loads(path.read_bytes())
            values = data["row"]
            # JSON arrays must regain the closed tuple fields before validation.
            for field in fields(ExitCriterionEvidence):
                if isinstance(getattr(row, field.name), tuple):
                    values[field.name] = tuple(values[field.name])
            candidate = ExitCriterionEvidence(**values)
            if (
                candidate.criterion != row.criterion
                or candidate.subject_revision != row.subject_revision
                or candidate.dirty_diff_sha256 != row.dirty_diff_sha256
                or candidate.test_nodes != row.test_nodes
                or candidate.owning_prs != row.owning_prs
                or candidate.contract_refs != row.contract_refs
            ):
                raise ValueError("owning record does not match the row and subject")
            if candidate.status in {"PASS", "DEFERRED"} and not verified_acceptance(
                candidate, root
            ):
                raise ValueError("owning acceptance could not be verified")
            loaded.append(candidate)
        except (OSError, ValueError, KeyError, TypeError):
            loaded.append(replace(row, reason=f"Missing or invalid OWNING_ACCEPTANCE: {path.name}"))
    return tuple(loaded)


def validate_exit(
    rows: tuple[ExitCriterionEvidence, ...], findings: tuple[str, ...], root: Path = ROOT
) -> str:
    if tuple(row.criterion for row in rows) != EXIT_CRITERIA:
        raise ValueError("all 19 literal exit rows required in order")
    identities = {(row.subject_revision, row.dirty_diff_sha256) for row in rows}
    if len(identities) != 1:
        raise ValueError("mixed evidence subjects")
    if any(item.startswith(("P0", "P1")) for item in findings):
        return "BLOCKED"
    for row in rows:
        if row.status not in {"PASS", "DEFERRED"}:
            return "BLOCKED"
        if not verified_acceptance(row, root):
            return "BLOCKED"
    return "PASS"


def verified_acceptance(row: ExitCriterionEvidence, root: Path) -> bool:
    """Verify owning assertions; deferrals cover only each cited owner-accepted gap."""
    if row.status == "DEFERRED":
        ref = EXIT_DEFERRALS.get(row.criterion)
        if ref is None or ref not in row.disposition_refs:
            return False
        disposition = (root / ref).resolve()
        if not disposition.is_relative_to(root.resolve()) or not disposition.is_file():
            return False
        if row.criterion != "PaperQA2 Adapter":
            # The named gap alone is deferred. All other owning assertions must pass.
            if row.failed or row.errors or row.skipped or not row.passed or not row.test_nodes:
                return False
        else:
            try:
                disposition = (root / B28_DISPOSITION).resolve()
                if not disposition.is_relative_to(root.resolve()) or not disposition.is_file():
                    return False
                packages = tomllib.loads((root / "uv.lock").read_text())["package"]
                if any(item["name"] in {"paper-qa", "paperqa"} for item in packages):
                    return False
                item = next(
                    item for item in adapter_inventory(root) if item.adapter_id == "paperqa2"
                )
                return (
                    item.status == "DEFERRED"
                    and item.mode == "DEFERRED"
                    and item.package_version is None
                )
            except (OSError, ValueError, KeyError, StopIteration):
                return False
    if row.status not in {"PASS", "DEFERRED"}:
        return False
    import re

    if (
        not row.acceptance_revision
        or not re.fullmatch("[0-9a-f]{40}", row.acceptance_revision)
        or not row.owning_prs
        or not row.contract_refs
        or not row.evidence_refs
        or not row.commands
        or any(row.exit_codes)
    ):
        return False
    for ref in (*row.contract_refs, *row.disposition_refs):
        path = (root / ref).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            return False
    if not row.disposition_refs:
        return False
    for node in row.test_nodes:
        path, separator, method = node.partition("::")
        target = (root / path).resolve()
        if not separator or not target.is_relative_to(root.resolve()) or not target.is_file():
            return False
        if not any(
            isinstance(item, ast.FunctionDef) and item.name == method.split("[")[0]
            for item in ast.walk(ast.parse(target.read_bytes()))
        ):
            return False
    for ref in row.evidence_refs:
        path = (root / ref).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            return False
    for ref in row.evidence_refs:
        path = root / ref
        if path.suffix != ".json":
            continue
        try:
            evidence = json.loads(path.read_bytes())
        except (ValueError, UnicodeError):
            continue
        if not isinstance(evidence, dict):
            continue
        if (
            evidence.get("scope") != "OWNING_ACCEPTANCE"
            or evidence.get("subject_revision") != row.subject_revision
            or evidence.get("dirty_diff_sha256") != row.dirty_diff_sha256
            or evidence.get("acceptance_revision") != row.acceptance_revision
            or evidence.get("mode") != "ENABLED"
            or evidence.get("optional") is not False
        ):
            continue
        if evidence.get("commands") != list(row.commands) or evidence.get("exit_codes") != list(
            row.exit_codes
        ):
            continue
        nodes = evidence.get("nodes", {})
        if not isinstance(nodes, dict) or not all(
            nodes.get(node) == "PASS" for node in row.test_nodes
        ):
            continue
        if evidence.get("counts") != dict(
            passed=row.passed, failed=row.failed, errors=row.errors, skipped=row.skipped
        ):
            continue
        logs = evidence.get("logs", [])
        if not logs or not set(logs) <= set(row.evidence_refs):
            continue
        if "row" in evidence:
            if evidence.get("criterion") != row.criterion:
                continue
            digests = evidence.get("log_sha256", {})
            if any(digests.get(ref) != digest_bytes((root / ref).read_bytes()) for ref in logs):
                continue
            cases = evidence.get("cases", [])
            if not cases or any(case.get("status") != "PASS" for case in cases):
                continue
            observed = {case.get("node", "").split("[")[0] for case in cases}
            if observed != set(row.test_nodes) or len(cases) != row.passed:
                continue
        return True
    return False


def verification_findings(directory: Path) -> tuple[str, ...]:
    path = directory / "verification.json"
    if not path.exists():
        return ()
    try:
        data = json.loads(path.read_bytes())
        return tuple(
            f"P1 MAJOR: verification command {item['label']} exited {item['exit_code']}"
            for item in data["results"]
            if item["exit_code"] != 0
        )
    except (OSError, ValueError, KeyError, TypeError):
        return ("P1 MAJOR: invalid focused verification record",)


def write_reports(root: Path = ROOT) -> Path:
    ctx = context(root)
    sha = subject_digest(ctx["subject_revision"], ctx["dirty_diff_sha256"])
    directory = root / SUBJECT_PREFIX / sha
    directory.mkdir(parents=True, exist_ok=True)
    inventory, migrations, rows = (
        adapter_inventory(root),
        migration_inventory(root),
        exit_rows(root, acceptance_directory=directory),
    )
    for number, item in enumerate(inventory):
        (directory / f"adapter-{number}.json").write_bytes(to_bytes(item))
    for number, item in enumerate(rows):
        (directory / f"exit-{number:02d}.json").write_bytes(to_bytes(item))
    (directory / "migration_scripts.json").write_bytes(canonical_bytes(migrations))
    (directory / "subject.json").write_bytes(
        canonical_bytes(
            {
                "subject_revision": ctx["subject_revision"],
                "dirty_diff_sha256": ctx["dirty_diff_sha256"],
                "subject_sha256": sha,
                "digest_definition": "SHA256(git diff HEAD --binary excluding generated"
                " reports/evidence + NUL + canonical untracked pat"
                "h/digest inventory)",
                "excluded_generated_paths": GENERATED,
            }
        )
    )
    findings = verification_findings(directory)
    verdict = validate_exit(rows, findings, root)
    ref = "pr2_20_verification.md"
    intro = (
        f"Subject `{ctx['subject_revision']}`; dirty diff `{ctx['dirty_diff_sha256']}`.\n\n"
        f"Recorded evidence: [subject]({ref}#subject). This is engineering evidence. "
        f"Phase 2 exit is **{verdict}**; owner acceptance is separate.\n\n"
    )
    texts = {}
    texts[REPORT_NAMES[0]] = (
        intro
        + "| Adapter | Mapping | Mode | API | License/advisory |\n| --- | --- | --- | --- | --- |\n"
        + "".join(
            f"| {item.adapter_id} | {item.mapping_version} | {item.mode} | "
            f"{item.api_profile} | BLOCKED: unresolved |\n"
            for item in inventory
        )
        + "\nExecution pins are distinct from reference-only harness.lock.yaml entries. "
        "No providers were enabled. The fake is not PaperQA2 acceptance. Local source"
        " and uv.lock SHA256 values are in the typed adapter records. Repository lice"
        "nse selection, upstream revision/license texts, notices, provider terms, cop"
        "yright/cache redistribution and dated advisory scan remain unresolved. No li"
        "cense permission or security clearance is inferred.\n"
    )
    texts[REPORT_NAMES[1]] = intro + (
        "Offline compatibility uses typed candidate contracts and disposable canonical-"
        "state manifests. "
        "Live provider acceptance remains BLOCKED; real PaperQA2 is owner-approved DEFERRED (B28). "
        "FakeScientificRAGCapability remains the deterministic gate. "
        "No STORM/PaperQA schema or executable pin is inferred from a reference.\n\n"
        "Transport destination validation rejects non-public literals and DNS answers before "
        "dispatch, pins the validated peer, disables proxies and redirects, and preserves "
        "HTTPS hostname verification. Offline security regressions verify this boundary. "
        "PaperQA index deserialization and corpus isolation remain deferred "
        "with the real adapter.\n"
    )
    texts[REPORT_NAMES[2]] = (
        intro
        + (
            "[Complete revision/predecessor/script digests](#revision-inventory). "
            "B31 adds no migration or index; B29 remains closed with zero B31 DDL. "
            f"The live head is {migrations[-1]['revision']}; "
            "the B31 boundary is 0068_b21_unresolved_capture, "
            "superseding the plan observation of 0042. "
            "Owning legacy predicates and populated downgrade refusals remain authoritative. "
            "Empty/no-op, reconnect, accepted populated checkpoints, rollback and histo"
            "rical-manifest tests "
            "are separate evidence; absent checkpoint acceptance remains BLOCKED.\n\n"
        )
        + "## Revision inventory\n\n"
        + migration_inventory_table(migrations)
    )

    def row_links(numbers: tuple[int, ...]) -> str:
        return (
            "\n".join(
                f"- [{rows[n - 1].criterion}]({ref}#exit-row-{n}): "
                f"{rows[n - 1].status}; {rows[n - 1].reason or 'owning assertions verified'}"
                for n in numbers
            )
            + "\n"
        )

    texts[REPORT_NAMES[3]] = (
        intro
        + (
            "The implemented literature trace starts with a frozen search plan and "
            "LiteratureSearchExecution query/result provenance. A persisted hit is resolved "
            "through the owning Application command to an exact frozen SourceVersion. "
            "Document ArtifactVersion bytes, hash and typed locator are checked before "
            "LiteratureEvidence admission; independent human review and sealed support "
            "snapshots preserve exact hashes and ordinals. Search hits and RAG candidates "
            "supply no scientific support by themselves. FakeScientificRAGCapability is "
            "the offline candidate boundary; B28 real PaperQA2 is DEFERRED.\n\n"
            "ScientificConclusion freeze closes its typed Claim and literature inputs. "
            "A manuscript places exact frozen Claim/conclusion versions, then freezes its "
            "placement set. Citation-only placement creates no Claim support. The downstream "
            "publication path enters internal review, records readiness Decision and Approval, "
            "consumes its grant at READY, prepares the authorship-bound package, records "
            "required consents, and consumes a separate preparation grant to create the "
            "FROZEN PreparedSubmissionVersion. Retraction/correction and finding/impact "
            "projections can make downstream material stale while preserving saved hashes, "
            "consumptions and frozen history. Fabricated or unresolved citations fail closed. "
            "These are composed owning scenarios; a lookup alone does not prove "
            "the full exit.\n\n"
            "Owning trace evidence (commands, nodes and counts are in each record):\n\n"
        )
        + row_links((2, 3, 4, 8, 9, 10, 11, 14, 15, 16))
    )
    texts[REPORT_NAMES[4]] = (
        intro
        + (
            "The implemented publication trace retains exact frozen Claim/conclusion IDs "
            "and hashes, experimental and literature support paths, and exact figure/document "
            "ArtifactVersion references. Manuscript freeze seals the placement set. Internal "
            "review records issues without rewriting that scientific material. A completed "
            "RevisionAction does not dispose an issue: independent re-review and the separate "
            "disposition command preserve concern history. M1 manuscript revision and "
            "reconsideration owning tests are included in the evidence inventory.\n\n"
            "After internal-review entry, the readiness Decision and Approval bind the frozen "
            "manuscript and complete review basis. transition_publication_ready consumes the "
            "readiness grant exactly once and records READY. Preparation binds the exact "
            "manuscript and AuthorshipSnapshot; AuthorConsent records bind the package. "
            "A separate PREPARE_SUBMISSION Decision/Approval grant and checked review set "
            "authorize freeze_prepared_submission, which validates the manifest and consents "
            "and creates the FROZEN PreparedSubmissionVersion atomically. Restart/replay "
            "returns the saved receipt through read authority; withdrawal and later invalidity "
            "remain new history or derived projections. B24 novelty outcomes never gate "
            "Approval, READY or package freeze. No external submission/send is asserted.\n\n"
            "Owning lifecycle evidence:\n\n"
        )
        + row_links((10, 12, 13, 14, 15))
    )
    texts[REPORT_NAMES[5]] = (
        intro + f"**Exit {verdict}.** Computed by validate_exit; this is not owner "
        "acceptance of Phase 2. The 19 literal criteria retain their frozen order. "
        "The Scientific RAG boundary is tested with the fake in the candidate/rejection "
        "records; it does not replace Row 6.\n\n"
        "| Literal exit criterion | Status | Reason | Evidence |\n| --- | --- | --- | --- |\n"
        + "".join(
            f"| {row.criterion} | {row.status} | {row.reason or 'Owning assertions verified'} | "
            f"[record]({ref}#exit-row-{number + 1}) |\n"
            for number, row in enumerate(rows)
        )
        + "\n| Architecture requirement | Concrete node | Disposition |\n| --- | --- | --- |\n"
        + "".join(
            f"| {name} | `{node}` | See owning Row 18 evidence |\n"
            for name, node in ARCHITECTURE_NODES.items()
        )
        + "\nOwner-accepted known gaps and scope dispositions:\n\n"
        + "\n".join(f"- {gap}" for gap in KNOWN_GAPS)
        + "\n\nFocused commands, exact counts and actual host details are in "
        "[verification](pr2_20_verification.md). Unrun, skipped, failed and blocked "
        "results stay distinct. Dedicated Linux host timing/attestation is owner-accepted "
        "DEFERRED for the benchmark-host part of Row 17 only; local macOS results remain "
        "informational and are not a substitute. "
        "Reference/provider revision, license/notice/terms and dated advisory review "
        "remain unresolved in the adapter inventory. No independent review or loop "
        "full-suite acceptance is inferred from these focused runs.\n\n"
        "**STOP; wait for explicit Phase 3 GO.**\n\n"
        "Owner decisions needed\n\n"
        + "".join(f"- {row.criterion}: {row.reason}\n" for row in rows if row.status == "BLOCKED")
        + "".join(f"- {finding}\n" for finding in findings)
        + "- Reference/provider intake: resolve revision, license/notice/terms and dated "
        "advisory review before enabling providers (adapter inventory).\n"
        + "- Attach independent review and loop full-suite evidence before owner exit decision.\n"
    )
    output = root / "docs/phase2"
    output.mkdir(parents=True, exist_ok=True)
    for name, body in texts.items():
        (output / name).write_text(body)
    return directory


EXIT_CRITERIA = (
    "LiteratureSource identity resolution",
    "SourceVersion lineage/freeze",
    "LiteratureSearchPlan/Run provenance",
    "LiteratureEvidence source+locator trace",
    "STORM-like Native ResearchStrategy",
    "PaperQA2 Adapter",
    "Academic Discussion explicit promotion",
    "ScientificConclusion support-set freeze",
    "ScientificConclusion Frozen Provenance Closure",
    "ManuscriptVersion scientific placement",
    "Citation ≠ ClaimSupport",
    "Internal Review → Issue → Decision → Revision",
    "Basic Approval frozen target / blocking gate",
    "SubmissionVersion package freeze",
    "Retracted-source impact propagation",
    "Hallucinated citation rejection",
    "PostgreSQL migrations/integration",
    "No STORM/PaperQA vendor-specific Core schema",
    "Phase 1 Exit tests continue",
)

ARCHITECTURE_NODES = {
    "test_literature_source_not_evidence": "tests/architecture/test_pr2_19_boundaries.p"
    "y::test_literature_source_not_evidence",
    "test_search_result_not_evidence": "tests/architecture/test_pr2_19_boundaries.py::t"
    "est_search_result_not_evidence",
    "test_citation_not_claim_support": "tests/architecture/test_pr2_19_boundaries.py::t"
    "est_citation_not_claim_support",
    "test_strategy_does_not_import_persistence": "tests/architecture/test_pr2_19_bounda"
    "ries.py::test_strategy_does_not_impor"
    "t_persistence",
    "test_adapter_does_not_write_db": "tests/architecture/test_pr2_19_boundaries.py::te"
    "st_adapter_does_not_write_db",
    "test_no_storm_specific_core_schema": "tests/architecture/test_pr2_19_boundaries.py"
    "::test_no_storm_specific_core_schema",
    "test_no_paperqa_specific_core_schema": "tests/architecture/test_pr2_19_boundaries."
    "py::test_no_paperqa_specific_core_schema",
    "test_discussion_not_canonical_science": "tests/architecture/test_pr2_19_boundaries"
    ".py::test_discussion_not_canonical_scienc"
    "e",
    "test_manuscript_not_scientific_source_of_truth": "tests/architecture/test_pr2_19_b"
    "oundaries.py::test_manuscript_no"
    "t_scientific_source_of_truth",
    "test_review_does_not_mutate_target": "tests/architecture/test_pr2_19_boundaries.py"
    "::test_review_does_not_mutate_target",
    "test_decision_does_not_mutate_history": "tests/architecture/test_pr2_19_boundaries"
    ".py::test_decision_does_not_mutate_histor"
    "y",
    "test_approval_does_not_override_invalid_fact": "tests/architecture/test_pr2_19_bou"
    "ndaries.py::test_approval_does_not"
    "_override_invalid_fact",
    "test_external_call_not_inside_long_db_transaction": "tests/architecture/test_pr2_1"
    "9_boundaries.py::test_externa"
    "l_call_not_inside_long_db_tra"
    "nsaction",
}


EXIT_OWNERS = dict(
    zip(
        EXIT_CRITERIA,
        (
            ("PR2-01",),
            ("PR2-02",),
            ("PR2-03", "PR2-04"),
            ("PR2-05",),
            ("PR2-08",),
            ("PR2-07",),
            ("PR2-10",),
            ("PR2-11",),
            ("PR2-11",),
            ("PR2-12", "PR2-13"),
            ("PR2-13", "PR2-19"),
            ("PR2-14", "PR2-15"),
            ("PR2-16",),
            ("PR2-17",),
            ("PR2-19",),
            ("PR2-19",),
            ("PR2-20",),
            ("PR2-20",),
            ("Phase 1 frozen baseline",),
        ),
        strict=True,
    )
)
B31_CONTRACT = "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md"
KNOWN_GAPS = (
    f"Dedicated Linux benchmark host not tested for now, owner 2026-10-20: "
    f"Row 17 benchmark-host part only DEFERRED; revisit before Phase 3 performance claims. "
    f"Local macOS timings are informational, not a substitute: {LINUX_DISPOSITION}.",
    f"B28 real PaperQA2 DEFERRED, owner 2026-10-19: {B28_DISPOSITION}.",
    f"AQ-S3-08, owner 2026-10-20: positive G2 AGENT admission test pending; "
    f"no Application path creates a bound AGENT. Never forge the binding: {AQ_S3}.",
    f"D-B31-03: B20 NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE (NO_CLOSE_PRIOR_ART), B23 "
    "novelty review/revision, and MANUSCRIPT_CHANGE remain Phase 2 exit non-goals: "
    f"{B31_CONTRACT}.",
)
# Each file is an owning acceptance suite, not a code-presence availability probe.
# All tests in each selected file are required, including every parametrized case.
_INTEGRATION = "tests/integration/phase2/"
_ROW_FILES = (
    ("test_pr2_01_source_identity.py",),
    ("test_pr2_02_source_version_migration.py", "test_pr2_19_lineage.py"),
    ("test_pr2_03_literature_search_plan_application.py", "test_pr2_04_execution_provenance.py"),
    ("test_m3_evidence.py", "test_pr2_19_search_evidence.py", "test_pr2_19_rag_evidence.py"),
    ("test_b02_strategy_capture.py", "test_b02_strategy_admission.py", "test_pr2_19_candidates.py"),
    (),
    (
        "test_b03_discussion_hypothesis.py",
        "test_b03_discussion_hypothesis_guards.py",
        "test_pr2_19_discussion.py",
    ),
    ("test_pr2_11_r2_persistence.py",),
    ("test_pr2_11_r2_persistence.py", "test_pr2_13_scientific_trace.py"),
    (
        "test_b04_manuscript_freeze.py",
        "test_pr2_13_scientific_trace.py",
        "test_pr2_19_citation_trace.py",
    ),
    ("test_pr2_19_citation_trace.py",),
    (
        "test_pr2_19_revision_cycle.py",
        "test_b07_revision_decisions.py",
        "test_b08_issue_disposition.py",
        "test_m1_manuscript_revision.py",
        "test_m1_manuscript_reconsideration.py",
    ),
    ("test_approval.py", "test_pr2_19_governance.py", "test_pr2_19_approval_atomicity.py"),
    (
        "test_pr2_19_package_freeze.py",
        "test_pr2_19_grant_consumption_publication.py",
        "test_b17_package_freeze.py",
    ),
    ("test_pr2_19_lineage.py", "test_b26_finding_impact.py", "test_b27_defensive_closure_read.py"),
    ("test_pr2_19_candidates.py", "test_pr2_19_integrity.py"),
    (
        "test_pr2_20_migrations.py",
        "test_pr2_20_catalog_plans.py",
        "test_pr2_20_security.py",
        "test_pr2_20_governance_races.py",
        "test_pr2_20_novelty.py",
    ),
    (),
    (),
)
EXIT_FILES = {
    criterion: tuple(_INTEGRATION + name for name in files)
    for criterion, files in zip(EXIT_CRITERIA, _ROW_FILES, strict=True)
}
EXIT_FILES[EXIT_CRITERIA[4]] += ("tests/unit/phase2/test_pr2_08_native_strategy.py",)
EXIT_FILES[EXIT_CRITERIA[15]] += ("tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py",)
# Attach the entire PR2-19 E2E inventory and bounded hardening observations;
# passing inventory assertions cannot override that inventory's BLOCKED full gate.
EXIT_FILES[EXIT_CRITERIA[16]] = tuple(
    sorted(
        {
            *EXIT_FILES[EXIT_CRITERIA[16]],
            *(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / _INTEGRATION).glob("test_pr2_19_*.py")
            ),
        }
    )
)
EXIT_FILES[EXIT_CRITERIA[17]] = ("tests/architecture/test_pr2_19_boundaries.py",)
EXIT_FILES[EXIT_CRITERIA[18]] = tuple(
    path.relative_to(ROOT).as_posix()
    for path in sorted((ROOT / "tests/e2e").glob("test_phase1_*.py"))
)
EXIT_NODES = {
    criterion: tuple(
        f"{path}::{node.name}"
        for path in paths
        for node in ast.parse((ROOT / path).read_bytes()).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
    for criterion, paths in EXIT_FILES.items()
}


if __name__ == "__main__":
    print(write_reports().relative_to(ROOT))


def compaction_inventory(root: Path = ROOT) -> tuple[dict[str, Any], ...]:
    """Inventory originals and literal consumers before any destructive compaction.

    No file is removed. Dynamic parsers need manual review, so every entry remains
    BLOCKED until its consumer and retained-history review is attached.
    """
    candidates = sorted(
        {
            *root.glob("docs/verification/task12/*/partition.json"),
            *(p for p in (root / "docs/verification/task14").rglob("*") if p.is_file()),
            *(
                p
                for p in (root / "pr_evidence").rglob("*")
                if p.is_file() and p.stat().st_size >= 100_000
            ),
        }
    )
    consumers = {}
    import subprocess

    listed = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    for item in listed.split(b"\0"):
        if item:
            path = root / item.decode()
            if path.is_file() and path.suffix in {".md", ".py", ".json", ".yml", ".yaml"}:
                consumers[item.decode()] = path.read_text(errors="replace")
    return tuple(
        dict(
            original_path=path.relative_to(root).as_posix(),
            original_bytes=path.stat().st_size,
            original_sha256=digest_bytes(path.read_bytes()),
            status="BLOCKED",
            reason="Retention and dynamic consumer recovery unapproved; original retained",
            consumers=sorted(
                name
                for name, body in consumers.items()
                if path.name in body or path.relative_to(root).as_posix() in body
            ),
        )
        for path in candidates
    )


def compaction_status(record, source_status: str) -> str:
    """Successful byte recovery never promotes the underlying execution result."""
    if source_status not in {"PASS", "FAIL", "BLOCKED", "NOT RUN", "DEFERRED"}:
        raise ValueError("invalid source result")
    return source_status if record.status == "PASS" else record.status
