# M2 live literature — partial implementation and contract blocker

Date: 2026-10-10 (Asia/Shanghai). **Verdict: M2_BLOCKED. M2 is not complete or ready for review acceptance.**

Starting SHA: `df603fe0fbb8c80758400e7b13cb831b7f730187` (exact approved M1 source verified).
Final implementation SHA: `d608a412d4982afe8a13816b34f9b2b4ef4c5d89`.
The subsequent delivery commit adds this report only; resolve its full SHA with `git log -1 --format=%H -- planning/M2_LIVE_LITERATURE_COMPLETION.md`. The final chat delivery records its exact SHA and bundle location.

Persistent worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m2-live-literature`; branch `feature/m2-live-literature`. The untracked M1 independent review report and original ResearchBase-phase2 user modification were preserved. No push, merge, history rewrite, canonical DB mutation, credential change, dependency addition or M3 work.

## Delivered and blocked behavior

Added a synchronous standard-library HTTP/OpenAlex Works adapter and focused offline tests. The adapter limits responses to 4 MiB, disables redirects/caches, maps stable Works IDs and DOI URLs, preserves order, translates frozen time/language filters, reports truncation, and classifies malformed/rate-limit/permanent/uncertain outcomes. It delegates retries to the existing execution service. Pre-dispatch cancellation proves NOT_SENT only and never fabricates provider-confirmed C1. `works-v1` identifies the ResearchBase request/response mapping; the unversioned public API exposes no vendor release version. No upstream package/binary was installed.

**Implemented CLI commands: none.** Existing plan/execution/source commands are unchanged. Production composition remains disabled for live providers and retains its existing fail-closed behavior. The adapter is partial code, not an enabled accepted workflow.

**Crossref, source resolution, persistence: not implemented.** [M2-AQ-001](M2_ARCHITECTURE_QUESTION.md) records the exact frozen-contract gap and a concrete narrow amendment proposal. PR2-04 §8 requires separately reviewed concrete ArtifactVersion linkage for retained responses. Field contract 13's resolution row has no observation-artifact FK and cannot represent a source-less conflicting/ambiguous/unavailable outcome. SourceVersion metadata forbids provider observation objects. Existing identifier verification owns state transitions, not a general observation history. Implementing durable conflicting observations by inventing columns or generic JSON would silently extend the frozen contract. Stop follows AGENTS §§4,11 and mission §9, not an extra Harness approval framework.

The proposed owner decision is a dependent append-only observation relation or explicit approved extension of the resolution pattern, with concrete result and frozen-artifact FKs, typed outcome, provider/version/time, project authorization and replay rules. No proposed schema has been implemented. This requires a revised field contract/ADR before the persistence path continues.

## Actual external request

The initial keyless one-result connectivity probe returned HTTP 200. A separate actual adapter request used `https://api.openalex.org/works`, search `CRISPR Cas9`, `per_page=2`, `page=1`, selected `id,title,doi,relevance_score`; no fake provider or cached fixture substituted for either call. Request began **2026-10-10 22:09:10.193665 Asia/Shanghai**, response retrieval completed **22:09:11.249453**. Two ordered hits, `RESULTS_TRUNCATED`:

- `W2339144537`: “What is CRISPR/Cas9?” — DOI `10.1136/archdischild-2016-310459`.
- `W2554763217`: “CRISPR–Cas9 Structures and Mechanisms” — DOI `10.1146/annurev-biophys-062215-010822`.

Saved execution IDs/source IDs/source-version IDs: **none**. These calls establish connectivity and adapter parsing only. They do not prove trusted CLI identity, Crossref matching, canonical persistence, or restart readback. Secret-free operational output: `/private/tmp/rb-m2-live-adapter.json`. The sandboxed initial curl could not resolve DNS; the permitted external-network invocation succeeded. External connectivity is available; the blocker is architectural, not BLOCKED_BY_EXTERNAL_DEPENDENCY.

Official API documentation inspected: [OpenAlex authentication/limits](https://help.openalex.org/api/authentication/), [Crossref REST API](https://github.com/CrossRef/rest-api-doc). OpenAlex permits small keyless requests and caps pages at 100; this adapter retrieves one bounded page because the existing admitted limit is at most 100. No claim of exhaustive coverage.

## Verification and limitations

At final implementation content:

- Offline adapter pytest: **9 passed, 0 failed, 0 errors, 0 skipped**, exit 0; XML `/private/tmp/rb-m2-adapter.xml`. Successful ordered response, empty result, four malformed payloads including wrong entity, rate limit with single adapter invocation, uncertain timeout and pre-dispatch cancellation.
- Added four Python files: Ruff `check --no-cache` **PASS**; formatter **4 files already formatted**; Pyright **0 errors, 0 warnings, 0 informations**, exit 0. Pyright used the existing M1 Python environment explicitly; it printed that M2 has no `.venv`. No environment/lock changes.
- `git diff --check`: exit 0. Final status/bundle verification is recorded in the delivery message.
- PostgreSQL integration, migration/constraint/concurrency, duplicate DOI, conflicting DOI/title, missing DOI, expiry/project authorization, saved-result replay/dedup, M0/M1 regressions and application restart: **NOT RUN for M2**. No migration/composition/persistence path changed. Prior M1 evidence is context, not a new test PASS.
- Full required real end-to-end demonstration: **NOT RUN / BLOCKED_BY_FROZEN_CONTRACT**. The standalone live request above is not acceptance.
- M0 response-reuse/cancellation normalization P2: **OPEN / not reviewed to closure**. The new adapter is disabled and does not yet alter production response consumption; reassess and cover it before activation. Five M1 retry-count assertion failures remain deferred, unchanged and not rerun.
- HTTP transport deadline/redirect/byte-limit behavior lacks dedicated transport-level tests; real OpenAlex exercised its ordinary successful path only. No independent implementation review or production activation gate is claimed.

## Remaining issues and readiness

**P1 MAJOR:** M2-AQ-001, missing approved durable observation/provenance storage contract blocks the required resolution/verification workflow. This is a specification blocker, not a demonstrated data-corruption incident. No P0 defect identified in this bounded work; full-system P0/P1 absence has not been established.

**P2 MINOR:** M0 response-reuse normalization review remains open; five inherited M1 retry-count cases remain deferred; adapter transport/error/filter coverage and activation requirements remain incomplete.

**M3 recommendation: NO_GO.** Resolve the contract question, finish M2 Crossref/source resolution and trusted CLI composition, run the full focused PostgreSQL/regression suite and actual CLI/restart demonstration, then obtain M2 review. Stop here; no M3 was started.
