# M2 live literature completion

**Verdict: M2_READY_FOR_REVIEW.** Date: 2026-10-10, Asia/Shanghai. This supersedes the earlier blocked report; M2-AQ-001 was explicitly approved and implemented. Independent review/acceptance is still pending. M3 has not begun.

Preserved baseline: `1a274da64aa6bda444c1bbf5df410d26bde89560` (ancestor of this delivery). Final implementation SHA: **`f6fd4bdbd62d6145153d4d65ed0fbc19f671e2be`**. The subsequent report-only delivery commit changes this file alone; its exact final SHA is `git log -1 --format=%H -- planning/M2_LIVE_LITERATURE_COMPLETION.md` and is recorded in the final delivery message. A commit cannot contain its own hash.

Worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m2-live-literature`, branch `feature/m2-live-literature`. Original M1 independent review and ResearchBase-phase2 execution-pack edits were preserved. No dependency/lock changes, push, merge, history rewrite, scientific evidence, source merging or M3 work.

## Delivered contract and behavior

[ADR-0013](../docs/architecture/adr/ADR-0013-durable-metadata-observations.md) and frozen Field Contract 13 amendment specify exact columns, FKs, nullability, unique replay key, checks, hashes, transaction boundaries and compatibility. Migration **0029_metadata_observations → parent 0028_provider_cancellation** adds one dependent MetadataObservation relation and the already specified SearchResultResolution relation. Existing scientific hashes and migrations remain intact.

- Concrete immutable result→query→execution→frozen plan traceability, project guards, frozen ArtifactVersion evidence FK, optional same-source version FK, RESTRICT deletes, and append-only triggers. Observations need no source to exist. This implementation leaves optional observation source pointers null; established source/version relationships remain in resolutions.
- Outcomes MATCH, CONFLICT, AMBIGUOUS, UNRESOLVED and UNAVAILABLE. Missing DOI produces a retained local identity assessment without external dispatch. Received HTTP/malformed/partial responses retain permitted bibliographic evidence, status and digest. Timeout before any HTTP response is response-less UNAVAILABLE with durable transport failure code, endpoint and attempt times. Retention failures propagate and commit no observation.
- Unique replay `(deployment_id, project_id, observed_by, invocation_id)` with request fingerprint binding exact result/hash, DOI, provider/mapping/endpoint and timeout. Same invocation/input replays; changed fingerprint fails; a distinct invocation permits a new request. Per-invocation local lock and fsynced operational dispatch journal prevent concurrent redispatch and database-retry reinvocation. An intent-only crash refuses redispatch rather than inventing response facts.
- CAS file data and directory entries sync before the observation transaction. Fresh authority validation and frozen Artifact/ArtifactVersion plus observation commit atomically; uncertain commit recovers by the same replay key. Failed transactions may leave harmless unreferenced CAS bytes. Missing evidence fails closed on read. DB, local identity/config, journal and CAS must be backed up together; a Git bundle contains code, not installation state.
- Real Crossref singleton DOI adapter retains redacted bibliographic fields and conflicts; DOI/title matching distinguishes ambiguous evidence from unavailable transport. OpenAlex selected result fields do not include author/date/publication-identifier metadata, so those comparisons explicitly state ORIGIN_NOT_AVAILABLE. Matching is bibliographic identity, not scientific truth.
- Resolution uses existing project-scoped source identity/version commands and deterministic subrequest IDs. Canonical DOI verification cites the exact observation artifact. New versions contain only curated metadata; fulltext/correction-basis remain null. Existing frozen versions are never overwritten. Incompatible existing source identity fails closed.
- Trusted local CLI enables plan/execution/source/version and new `literature-metadata observe/get/list/resolve`. Local `question-freeze` uses the existing Application command with fresh project authorization; actor forgery is rejected. Finite PostgreSQL Decimal scores serialize losslessly as strings. Existing OpenAlex adapter/tests are preserved.

## Real external-provider acceptance

Fresh trusted OS-user installation, real network responses, PostgreSQL **18.6 (Homebrew), UTC**. No fake provider substituted in the demonstration. Full CLI script started **2026-10-10T14:59:48.958752+00:00**, finished **2026-10-10T15:00:01.661917+00:00** (UTC).

Actor `18736df0-d667-4bf5-8d14-2e123881437c`; project `0ecdbd9a-b426-4814-b245-7c382dfae708`; execution **`64fc8345-a7b4-49c8-922b-5196b3b719b8`**; frozen plan version `f9779c10-d8e0-48b4-960f-eea20d3d8390`. Execution **SUCCEEDED**, real OpenAlex query `CRISPR Cas9 Structures and Mechanisms`, bounded two-result page. Search execution retains original provider order/scores, request attempts, events, query hashes and frozen plan provenance. This bounded page does not claim exhaustive retrieval.

- **W2554763217** — CRISPR–Cas9 Structures and Mechanisms
  DOI `10.1146/annurev-biophys-062215-010822`; Crossref HTTP 200, **MATCH**, observed `2026-10-10T14:59:55.952846+00:00`.
  Result `0a9fffa5-a315-4fc3-ba57-f85f399f5d7b`; observation `fd1f6e9e-1463-4716-a7d7-da0b36d333d5`; exact ArtifactVersion `7e844ff6-3fb7-47ae-93f2-84a02766baa0`.
  Source `83dd4522-bc4f-4c0a-9c96-8ab3a6a692f0`; frozen SourceVersion `9a318e69-bb33-4bb4-a988-e683006c3747`; resolution `bf9aec75-d1b2-4acd-9c60-183f5a68c36a`.
  Retained response digest `45f5a2ddc7b398fae602c70a1af12e38ddb7a4a26de0543e8f212b90aff2f40a`.
- **W4234193230** — Faculty Opinions recommendation of CRISPR-Cas9 Structures and Mechanisms.
  DOI `10.3410/f.727477545.793535855`; Crossref HTTP 200, **MATCH**, observed `2026-10-10T14:59:59.386393+00:00`.
  Result `e10210ae-1893-4e42-ae43-ca35c20964c6`; observation `0dd45582-06f9-4711-b1e2-4759d9fd0018`; exact ArtifactVersion `05cbf275-a6c4-4b92-8c5e-37b3a6ffa9bd`.
  Source `7f7156a8-eeb5-4dc4-a58e-eb43dc7bf1dd`; frozen SourceVersion `c25771ea-bb0e-4e3c-ba3e-7109f358fcd1`; resolution `c8b0b0a5-d058-4ff2-8ecb-facf2a01b829`.
  Retained response digest `7ab974ddd2443a68e448a94542182a02816bb8c05a62d9593f807db2fc520e83`.

The second provider record is a Crossref dataset-type recommendation; its bibliographic source/version is conservatively OTHER, not relabelled as a research paper. Both resolutions are established relationships, not Claim support.

Separate authenticated CLI processes read each observation/evidence, source and frozen version, and re-read execution provenance with exact equality. Final SQL verified migration head 0029, **2 MATCH observations, 2 resolutions, 2 FROZEN SourceVersions and 2 FROZEN evidence ArtifactVersions**. Full secret-free execution/command transcript: `/private/tmp/rb-m2-live-final.json`. Live DB: `researchbase_m2_final` on `127.0.0.1:55440`; local installation `/private/tmp/rb-m2-final-installation`; CAS/journal `/private/tmp/rb-m2-final-artifacts`. These temporary operational files are not included in Git.

## Executable commands

The verified run used the existing M1 uv-managed environment; no parallel dependency definition or new runtime package was introduced. From the M2 worktree:

```bash
export PYTHONPATH=src
RB_PYTHON=../m1-identity-onboarding/.venv/bin/python
export DATABASE_URL=postgresql+psycopg://onephone@127.0.0.1:55440/researchbase_m2_final
export RESEARCHBASE_LOCAL_ROOT=/private/tmp/rb-m2-final-installation
export ARTIFACT_STORE_ROOT=/private/tmp/rb-m2-final-artifacts
"$RB_PYTHON" -m researchbase.cli.main literature-search-execution provenance --project-id 0ecdbd9a-b426-4814-b245-7c382dfae708 --execution-id 64fc8345-a7b4-49c8-922b-5196b3b719b8 --json
"$RB_PYTHON" -m researchbase.cli.main literature-metadata get --project-id 0ecdbd9a-b426-4814-b245-7c382dfae708 --observation-id fd1f6e9e-1463-4716-a7d7-da0b36d333d5 --json
"$RB_PYTHON" -m researchbase.cli.main literature-metadata list --project-id 0ecdbd9a-b426-4814-b245-7c382dfae708 --result-id 0a9fffa5-a315-4fc3-ba57-f85f399f5d7b --json
# Exact invocation replay; does not make a new provider request:
"$RB_PYTHON" -m researchbase.cli.main --request-id e3af3db8-d66c-41e6-8a02-072966d83ddb literature-metadata observe --project-id 0ecdbd9a-b426-4814-b245-7c382dfae708 --result-id 0a9fffa5-a315-4fc3-ba57-f85f399f5d7b --json
"$RB_PYTHON" -m researchbase.cli.main literature-metadata resolve --project-id 0ecdbd9a-b426-4814-b245-7c382dfae708 --observation-id fd1f6e9e-1463-4716-a7d7-da0b36d333d5 --json
```

For a fresh complete run, use a new disposable database and new installation/CAS directories (not the completed installation):

```bash
/opt/homebrew/opt/postgresql@18/bin/createdb -h 127.0.0.1 -p 55440 researchbase_m2_review_demo
export DATABASE_URL=postgresql+psycopg://onephone@127.0.0.1:55440/researchbase_m2_review_demo
export RESEARCHBASE_LOCAL_ROOT=/private/tmp/rb-m2-review-installation
export ARTIFACT_STORE_ROOT=/private/tmp/rb-m2-review-artifacts
"$RB_PYTHON" -m alembic upgrade head
"$RB_PYTHON" scripts/m2_live_demo.py --output /private/tmp/rb-m2-review-live.json
```

The script executes local init/bootstrap, question create/freeze, plan create/freeze, OpenAlex create/execute/provenance, Crossref observe/get, resolution, source/version reads and restart readback. Use a stable global `--request-id` for each observation invocation; new IDs intentionally authorize new external requests. Optional OPENALEX_API_KEY is read only from environment and not retained in evidence.

## Verification

- **M2 acceptance: 38 passed, 0 failed/errors/skipped**, exit 0, `/private/tmp/rb-m2-acceptance-final.xml`. 22 unit cases (including all 9 preserved OpenAlex cases) and 16 real-PostgreSQL cases. Covers all five outcomes, received 404 and no-DOI distinction, partial-body timeout, redaction/conflict retention, replay/fingerprint conflict, concurrent insertion with one dispatch, new invocation, source/resolution dedup, actual foreign-project denial, missing CAS/invalid artifact reference, null MATCH artifact rejection, storage failure, DB retry, lost commit acknowledgement, expiry during HTTP, append-only history, separate-process readback, fresh/roundtrip migrations, populated downgrade refusal and direct question-freeze actor forgery.
- **Focused M0/M1 regressions: 83 passed, 0 failed/errors/skipped**, exit 0, `/private/tmp/rb-m2-regressions-final.xml`; one known diagnostic case explicitly deselected. Covers local identity/onboarding, credential expiry while waiting for locks, project/role/credential authorization, cancellation, commit faults, partial-result recovery, restart and layering.
- Initial wider regression invocation: 82 passed, 2 failed of 84. The obsolete M0 migration-head expectation was corrected for additive 0029 and passes on rerun. The other failure is historical diagnostic serialization (see below); no failure is presented as PASS.
- Ruff check **PASS**, formatter **22 files already formatted**, modified/new Python plus M0 migration test. Pyright **0 errors, 0 warnings, 0 informations** on 21 modified/new Python files using explicit existing Python environment. Pyright notes M2 has no local `.venv`; Alembic emits existing `path_separator` deprecation warnings. `git diff --check` PASS.
- Final code real-provider CLI acceptance **PASS**, actual SQL counts above; no inference from the previous standalone connectivity probe. Full historical/full-repository suite and production deployment validation **not run**.

Reproduce focused M2 tests with the test maintenance DATABASE_URL ending `/postgres` (fixture creates/drops disposable databases):

```bash
DATABASE_URL=postgresql+psycopg://onephone@127.0.0.1:55440/postgres "$RB_PYTHON" -m pytest tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/test_m2_journal.py tests/unit/test_m2_cli_output.py tests/unit/test_m2_artifact_durability.py tests/integration/phase2/test_m2_metadata.py -q -p no:cacheprovider
```

## Unresolved defects, limits and M3 readiness

No open newly identified M2 P0 BLOCKER/P1 MAJOR remains in this bounded verification; independent review is pending. Remaining items are not silently marked fixed:

- **Historical P2 diagnostic debt:** `test_pg_equal_created_at_cursor_uses_uuid_tiebreak_without_duplicates_or_omissions` fails in `scripts/pr2_04_pytest_evidence.py:26` because the evidence recorder cannot JSON-serialize a database scalar. Reproduced on untouched archived baseline `1a274da…`, with baseline migrations/head 0028 and identical TypeError; `/private/tmp/rb-m2-baseline-cursor.xml`. Product cursor assertions precede that recorder, but the test is still FAILED, not PASS. No unrelated diagnostic repair.
- **Historical P2 M0 normalization debt:** confirmed C1 cancellation with a non-null Retry-After can mismatch sealed response reuse because the cancellation branch normalizes Retry-After differently. Inspected and left open. Live OpenAlex never returns provider-confirmed C1/PROVIDER_CANCELLED; pre-dispatch cancellation is NOT_SENT and uncertain transport remains UNKNOWN. Existing C1/cancellation regressions pass for their covered cases. This debt is not activated by the live adapter and is not claimed resolved.
- Five inherited M1 retry-count assertion cases remain deferred and **not rerun**; the full historical suite is not green by assertion.
- **P2 transport limitation:** urllib socket/read timeout is not a hard process-kill wall-clock deadline against a slow streaming peer; bounded reads check elapsed time between reads. Header/partial-body facts are retained on read failure. Independent transport stress testing and provider rate-policy/retention review beyond this local milestone remain future work. No queued/background resolver, exhaustive search, distributed/multi-host dispatch journal or API activation is provided.
- Source resolution conservatively rejects incompatible existing identity; it does not merge sources or revise existing frozen metadata. An interrupted intent-only external dispatch needs an explicitly distinct invocation ID. Legal retention is restricted to bibliographic whitelist fields; abstracts/full text/credentials/headers are omitted.

**M3 readiness: M2 is ready for independent review, not authorization to begin M3.** Review this exact implementation and evidence, resolve acceptance findings and explicitly authorize M3 separately. No M3 features were implemented.

## Delivery

One new code milestone bundle is created after the report-only delivery commit at `/Users/onephone/Documents/Codex/ResearchBaseProject/backups/m2-live-literature-milestone.bundle`; the earlier `m2-live-literature-1a274da.bundle` remains preserved. Final delivery verifies bundle integrity, required baseline ancestry and clean feature-worktree status, and records the exact delivery SHA. No push or merge.
