# M1 Identity and Onboarding — blocked execution report

Date: 2026-10-10 (Asia/Shanghai). Verdict: **M1_BLOCKED**.

## Candidate and changes

Starting SHA and final implementation SHA: `eac3153cd3ba96797d63593827ec58fc8d3fc1a6`.
The approved `f2-p1-c03` checkout was clean at that exact SHA. Created the requested persistent worktree `worktrees/m1-identity-onboarding` and branch `feature/m1-identity-onboarding` from it. Production source, migrations, dependency declarations and lockfile are unchanged. The delivery commit contains this report only; obtain its SHA with `git log -1 --format=%H -- planning/M1_IDENTITY_ONBOARDING_COMPLETION.md`.

`uv sync --frozen` succeeded with Python 3.12.14. No new user-visible authentication capabilities or onboarding commands were implemented. Existing literature CLI/API routes still require an externally established verified principal; production composition still supplies no trusted verifier. No M1 usability or security acceptance is claimed.

## P1 MAJOR — first local owner has no approved HTTP credential enrollment path

Evidence and contract:

- Contract 16, “Boundary and principal model,” paragraphs 1–3 and first-bootstrap ceremony: local CLI authenticates kernel UID; HTTP authenticates a CA-verified client certificate and resolves an `MTLS_URI` binding. Bootstrap creates an `OS_UID` binding and non-null `local-os:<deployment>:<uid>` external key. Neither actor ID nor proxy headers establish authentication.
- `src/researchbase/application/phase2_identity.py:325–369`: bootstrap implements that OS-only binding.
- Contract 16 legacy ceremony; Application lines 478–507 and 1342–1379: legacy binding applies only to an actor with null external key and no existing active binding. It cannot add an mTLS subject to the bootstrapped owner.
- Contract 16 provisioning ceremony; Application lines 1214–1233 and 1282–1309: provisioning requires independent operator/subject proof, rejects operator equal to the current owner, and creates a new actor. It does not attach a second credential to an existing actor.
- Contract 12 §3 also requires a separate certificate-issuance ceremony. Issuing a certificate alone does not create the required canonical subject binding.

Impact: for a fresh installation with only the bootstrapped local user and no independent onboarding operator, an HTTP verifier alone cannot produce an authorized principal under the approved ceremonies. Adding an mTLS binding directly, treating an OS binding as an mTLS binding, weakening independence, or accepting caller headers would bypass the identity contracts. A deployment with an independently verified operator and a separately provisioned HTTP actor is a different viable profile, but its availability has not been established for this single-user mission.

This is a contract-completeness decision, not an observed authentication bypass. Existing fail-closed behavior remains intact. The mission explicitly says to STOP for a frozen-contract conflict or unresolved identity trust-boundary decision; implementation stopped before changing that boundary.

## Concrete resolution requested

Recommended architecture clarification: authorize a dedicated first-owner HTTP credential enrollment ceremony for the already authenticated bootstrap actor. Require a live allowlisted kernel-UID principal matching the immutable bootstrap binding, fresh proof of possession of the proposed mTLS private key through a CA-verified handshake, a fresh single-use challenge bound to actor/deployment/exact URI/certificate fingerprint, a protected signed audit record before commit, SERIALIZABLE deployment/project locking, and fresh post-lock credential/challenge checks. Append the additional binding and binding event without changing actor attribution or membership. Explicitly decide whether the initial owner may perform this narrow ceremony without an independent operator, and specify its binding-event/challenge representation before code: existing event kinds and legacy challenge constraints must not be silently repurposed. A certificate remains insufficient without this enrollment.

Alternative retaining current contracts: require an independent deployment operator and provision a separate mTLS actor with explicit project membership. This requires confirmation of that deployment profile. A CLI-only M1 would instead require an explicit scope reduction; it would not satisfy the original API requirement.

No architecture exception or new ceremony is approved by this report.

## Verification actually executed

| Check | Result |
|---|---|
| Approved checkout HEAD and porcelain status | Exact approved SHA; clean |
| Requested worktree/branch creation | Succeeded from exact approved SHA |
| `uv sync --frozen` | Exit 0; existing locked dependencies only |
| `uv run --frozen pytest -o addopts='' tests/architecture/test_pr2_00_boundaries.py -q` | Exit 0; **3 passed in 2.29s** |
| Source/migration/pyproject/lock diff against starting SHA | Empty; exit 0 |
| End-to-end onboarding, restart, invalid/revoked/expired and cross-project smoke | **NOT RUN**; real adapters and approved HTTP enrollment unavailable |
| PostgreSQL identity/membership/bootstrap/temporal/CLI/API/M0 regressions | **NOT RUN**; stopped at contract decision; no cluster initialized |
| Ruff/formatter/Pyright on modified Python paths | Not applicable; no Python paths changed |
| Repository-wide diagnostics | Not run; no claim about baseline debt or full-suite success |

## Remaining issues, delivery and next milestone

P0: none identified in this bounded inspection; no independent M1 security review performed.
P1: the HTTP enrollment decision above blocks the requested complete single-user onboarding profile.
P2: carry forward M0 cancellation response-reuse metadata mismatch (`literature_search_execution.py:1408/1534` in the starting candidate); untouched. Historical repository-wide diagnostics remain unassessed.

Deferred: all M1 implementation and real acceptance demonstrations pending resolution; OpenAlex, Crossref and all M2 work remain excluded. **Not ready for M2 live literature search.** No push, merge, scientific data write or historical rewrite occurred. The requested local milestone backup is created and verified after the report commit; it preserves this blocked checkpoint, not a completed M1 implementation.
