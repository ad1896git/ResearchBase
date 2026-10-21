# M1 Identity and Onboarding — local-first completion

Date: 2026-10-10 (Asia/Shanghai). Verdict: **M1_READY_FOR_REVIEW**.

## Checkpoint and scope

Starting SHA: `ed0f00ddd26132ed99b61578a606f05c4453949a`.
Final implementation SHA: `da3db317aae30095a3cdbeaaca713fc06fc2c913`.
The subsequent delivery commit changes this report only. Obtain its exact SHA with `git log -1 --format=%H -- planning/M1_IDENTITY_ONBOARDING_COMPLETION.md`; the delivery message supplies that SHA and the verified bundle location.

Reused `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding`, branch `feature/m1-identity-onboarding`. The starting worktree was clean. Approved M0 `eac3153cd3ba96797d63593827ec58fc8d3fc1a6` remains an ancestor. No extra worktree, history rewrite, push, merge, schema migration, runtime dependency or M2 implementation.

[ADR-0012](../docs/architecture/adr/ADR-0012-local-first-identity.md) records architecture-owner decision M1-AUTH-002. It supersedes certificate enrollment for this local profile only. Prior PKI blockers are resolved by the approved scope change; network authentication is unchanged.

## Delivered path and trust boundary

Actual kernel real/effective UID and GID must agree; root and setuid/setgid invocation fail closed. USER, LOGNAME, SUDO_UID, HOME, headers and actor flags cannot establish identity. The OS account database supplies the default configuration directory. Host identity, installation UUID, physical configuration path and credential ID bind the OS UID to the existing canonical Actor through the existing OS_UID binding, bootstrap record and external key. No missing mapping creates another Owner.

A new dedicated mode-0700 directory holds mode-0600 operational policy, bootstrap secret, HMAC audit key and proof records. Reads reject symlinks, unexpected ownership, group/other permissions, nonregular files and hardlinks. Policy is reread at fresh database authorization time after project/authority locks. Existing Application bootstrap performs the canonical atomic transaction and permanently closes globally; the local bootstrap secret is invalidated after commit. Authenticated HMAC proof is retained without logging secret bytes.

Production composition supplies the real verifier to existing identity and literature services. Exposed Phase 1 workspace/research-question commands enforce actual actor and project authorization inside their existing UoW transaction. All canonical writes use Application services and repository ports. Archived projects retain authorized historical reads but deny new research writes. Other legacy CLI groups fail closed pending separately scoped composition. HTTP remains fail closed, including localhost/header attempts, and CLI starts no listener.

The trusted OS account, its configuration, executing code and database administration credentials form the boundary. This is not isolation from malicious code running under that same account. Local HMAC audit integrity is not independent operator nonrepudiation. Cloned platform identifiers, privileged UID reuse and account/database compromise are outside the guarantee. Untrusted Agents must not inherit this account or its database privileges; no sandbox is supplied.

## Actual user-facing commands

Run in the existing checkout under the intended non-root account. Set DATABASE_URL through protected deployment configuration; keep server/session timezone UTC. The same installation directory and database must be used after restarting the CLI. UUID placeholders below are replaced with returned IDs; use a fresh request UUID for creation.

```bash
uv sync --frozen
uv run alembic upgrade head
uv run researchbase local init --json
uv run researchbase local bootstrap --display-name "Researcher" --project-name "My research" --json
uv run researchbase local whoami --json
uv run researchbase local project-show --project-id PROJECT_UUID --json
uv run researchbase local workspace-create --project-id PROJECT_UUID --name Lab --locator /absolute/workspace --json
uv run researchbase local question-create --project-id PROJECT_UUID --question-text "What explains this result?" --json
uv run researchbase local question-show --question-id QUESTION_UUID --json
uv run researchbase --request-id REQUEST_UUID literature search-plan create --project-id PROJECT_UUID --material-json '{"objective":"Review relevant work","source_scope":"BIBLIOGRAPHIC","search_strategy":"KEYWORD","planned_providers":["openalex"]}' --json
uv run researchbase literature search-plan show --project-id PROJECT_UUID --plan-id PLAN_UUID --json
```

`openalex` is planned material, not a live provider call. Default local state is `.researchbase-local` in the OS account's actual home; optional RESEARCHBASE_LOCAL_ROOT selects a dedicated physical path outside Git checkouts. Repeated init refuses to overwrite. Preserve protected installation/audit files alongside database backups. Missing binding, lost configuration and relocation require future explicit recovery/enrollment; existing databases are never automatically re-bootstrapped.

## Verification evidence

Used actual macOS UID from the running process, separate production CLI subprocesses, Alembic migration head and real disposable PostgreSQL **18.6**, timezone **UTC**, port 55438. No SQLite or fake positive principal. Fixture-created identities are used only for negative cross-project/membership setup. No user-owned database was modified.

- Final local identity/onboarding plus existing temporal/concurrency selection: **17 passed, 0 failed, 0 errors, 0 skipped**. XML `/private/tmp/rb-m1-security-final.xml`.
- Final broader selection (below): **80 passed, 5 failed, 0 errors, 0 skipped (85 cases)**. XML `/private/tmp/rb-m1-final.xml`.
- CLI contract and C01/C02 unit regression selection: **15 passed, 3 deselected**; the historical-specific cases excluded by the explicit `-k` filter are not claimed as passes. XML `/private/tmp/rb-m1-unit-regressions.xml`.
- Five failing authority-race cases reproduced at exact starting SHA from a read-only `git archive` extraction: **5 failed, 3 deselected**, XML `/private/tmp/rb-m1-baseline-races.xml`. They fail the existing `AUTHORITY_RACE_RETRY_MASKING_CONFIRMED` assertion requiring exactly one attempt; actual behavior retries a serialization failure and then rejects with FORBIDDEN. The no-effect/authority-denial assertions pass. No assertion was weakened and no existing authority implementation was changed. These failures are recorded, not converted to PASS.
- Modified ten Python files: Ruff check passes; Ruff format check reports ten already formatted; Pyright reports **0 errors, 0 warnings**. Full repository comparison against starting SHA: Ruff **394 → 393**, Pyright **81 → 81**, **zero new diagnostics** (normalized repository path/rule/message). Existing lint debt remains. Delta `/private/tmp/rb-m1-diagnostic-delta.json`.
- `git diff --check`: passes. Core changes received a bounded primary-executor security/contract review; independent review remains the next stage.

The subprocess smoke proves real OS user → verified local principal → canonical Actor → Owner membership → CLI Application command → PostgreSQL → exact canonical readback after process restart. It covers project/workspace, ResearchQuestion, literature search plan and an existing source command. Concurrent CLI bootstrap produces exactly one successful canonical bootstrap and one closed rejection, with single Actor/Project/bootstrap record.

Rejected cases include actor overrides, alternate supplied UID, foreign/copy installation, forged username/environment identity, expired/disabled local policy, insecure/symlinked files, mocked root/effective-UID transitions, repeated bootstrap, foreign project, suspended membership, revoked binding and direct forged Application actor attribution. Credential expiry during both observed advisory and project-row lock waits returns FORBIDDEN with no research question committed. Existing HTTP TestClient attempts with localhost/actor header receive 401 without a network listener.

**Limitations:** a different real OS user was not available/tested; no accounts or host security settings were changed. Explicit negative UID/privilege branches use doubles and do not prove OS-level multi-user isolation. Linux machine-ID code was not executed on this macOS host. These limitations require review, not claims of multi-user or cross-platform acceptance.

Reproducible selections (with DATABASE_URL targeting only disposable PostgreSQL test infrastructure):

```bash
uv run pytest tests/unit/test_local_identity.py tests/integration/phase2/test_m1_local_onboarding.py tests/integration/phase2/test_pr2_00_temporal_auth.py tests/integration/phase2/test_pr2_00_concurrency.py -q
uv run pytest tests/architecture/test_pr2_00_boundaries.py tests/integration/phase2/test_lean_p1_sql.py tests/integration/phase2/test_m0_provider_cancellation.py tests/integration/phase2/test_m1_local_onboarding.py tests/integration/phase2/test_pr2_00_bootstrap.py tests/integration/phase2/test_pr2_00_concurrency.py tests/integration/phase2/test_pr2_00_identity.py tests/integration/phase2/test_pr2_00_ownership.py tests/integration/phase2/test_pr2_00_temporal_auth.py tests/integration/phase2/test_pr2_03_effective_authority.py tests/unit/test_local_identity.py -q
uv run pytest tests/unit/test_pr16_cli_contract.py tests/unit/phase2/test_lean_p1_regressions.py -k 'not historical' -q
```

Focused Ruff/format/Pyright were each run on `src/researchbase/local_identity.py`, `application/{local_workbench,commands,ports}.py`, `cli/{app,composition}.py`, `cli/commands/local.py`, `persistence/phase2_identity_repository.py`, `tests/unit/test_local_identity.py`, and `tests/integration/phase2/test_m1_local_onboarding.py` (source paths rooted at `src/researchbase`). Repository-wide diagnostic runs exit nonzero for the documented baseline debt.

## Remaining issues and next stage

The five preexisting effective-authority retry-count failures remain test/diagnostic debt requiring independent assessment. The previously deferred M0 P2 cancellation retry_after normalization mismatch remains unchanged. Partial filesystem initialization requires inspection; automatic credential recovery/relocation and the remaining legacy CLI groups are deferred product work. No new P0/P1 defect was identified by the bounded author review; this is not an independent gate approval.

Deferred: live OpenAlex/Crossref retrieval (M2), PKI/mTLS enrollment, SSO, network and multi-user profiles, real different-user isolation, Agent sandboxing and installation recovery. Local M1 is ready for independent security/architecture review. M2 may be planned after that review; it was not begun. No production readiness or security closure claim is made.
