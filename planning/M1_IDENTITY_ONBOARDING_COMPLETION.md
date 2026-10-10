# M1 Identity and Onboarding — continuation checkpoint

Date: 2026-10-10 (Asia/Shanghai). Verdict: **M1_BLOCKED**.

## Starting and final state

Continuation starting SHA: `7e0dbb0eb3917df6796f149937a548b04922b2bc`.
Final implementation SHA: the same SHA; no production implementation changed. The final delivery commit changes this report only; its exact SHA is available with `git log -1 --format=%H -- planning/M1_IDENTITY_ONBOARDING_COMPLETION.md` and is reported in the delivery message.

Verified the existing `feature/m1-identity-onboarding` branch and clean worktree at `worktrees/m1-identity-onboarding`. Both the approved M0 SHA `eac3153cd3ba96797d63593827ec58fc8d3fc1a6` and the expected M1 checkpoint are ancestors of HEAD (each check exit 0). Reused the existing worktree. No history was rewritten.

## Approved decision: M1-AUTH-001

The architecture owner's continuation authorization resolves the previous first-owner enrollment deadlock. A locally OS-authenticated, previously bootstrapped first Owner may enroll an mTLS credential for that existing identity through a protected local administration channel without requiring a preexisting mTLS credential or an independent operator. Ordinary HTTP endpoints still require mTLS. The former contract-completeness blocker is resolved and must not be raised again as an approval requirement.

This authorization does not establish a CA or issuer, approve arbitrary self-signed credentials, or substitute an insecure verifier. Its explicit prerequisite is: “If no operationally trustworthy certificate issuer, trust root, or mTLS verification path exists, identify the exact missing prerequisite and STOP rather than substituting an insecure verifier.”

## Current blocker: operational certificate trust prerequisites unavailable

The inspected project configuration and current process environment do not identify an approved certificate issuer or CA trust root. No operational mTLS verification path was found in the inspected project. This is a bounded observation, not a claim that no PKI exists elsewhere on the host or in the organization.

Evidence:

- `.env.example` contains only database and artifact-store settings. No `.env` exists in the M1 worktree.
- `compose.yaml` defines PostgreSQL only; it has no TLS ingress service.
- `src/researchbase/persistence/config.py:15–20` defines database URL, artifact root, log level and application environment only.
- `src/researchbase/api/app.py:74–111` supplies no credential verifier and installs no TLS authentication adapter.
- `src/researchbase/api/routes.py:653–668` requires an already verified principal; a header cannot create it.
- Filename searches in the project workspace found no TLS/ingress/issuer configuration or CA-named PEM/CRT files. No certificate/issuer environment variable names matching MTLS, TLS_, CLIENT_CERT, CA_BUNDLE, CA_FILE, ISSUER or TRUST_ROOT were present. No private keys or credential bytes were read.

Exact prerequisites needed to continue:

1. An approved deployment CA trust bundle and an identified operational issuer/issuance procedure for server and client-auth certificates. The issuer's private key must remain with the issuer; it must not be supplied in chat or committed.
2. The issuer's revocation mechanism and policy (for example, an available signed CRL with freshness requirements), plus the client URI SAN/Owner-binding policy.
3. The approved TLS termination configuration or authorization to implement direct TLS termination using that supplied trust root, including protected server certificate/key file paths. Client private-key possession must be proved through a real validated handshake; localhost alone is insufficient.

Resolution: provide the existing approved deployment configuration and public trust-root location, or explicitly authorize a separate, specified local PKI provisioning step with its ownership and trust policy. No new CA has been created or implicitly trusted. Implementation stopped at this prerequisite as instructed.

## Implementation, commands and trust boundaries

No new user-visible capabilities, onboarding commands, enrollment migration or credential verifier were implemented in this continuation. No runnable M1 enrollment command is claimed. Existing scientific provenance, M0 corrections and dependency lock remain unchanged.

The authorized design remains kernel-provided local UID authentication, a match to the immutable bootstrap Owner and existing membership, CA-validated client-auth certificate and private-key possession, one-time concurrent-safe persistent enrollment, and fresh post-lock authorization. HTTP must resolve the enrolled exact mTLS subject to that same Owner and recheck validity/revocation. These are requirements awaiting implementation, not verified capabilities.

## Verification actually executed

| Check | Result |
|---|---|
| `git status --short` and `git rev-parse HEAD` | Clean; exact expected checkpoint |
| `git merge-base --is-ancestor eac3153cd3ba96797d63593827ec58fc8d3fc1a6 HEAD` | Exit 0 |
| `git merge-base --is-ancestor 7e0dbb0 HEAD` | Exit 0 |
| Configuration/source and environment-name inspection | Missing prerequisites listed above; no secret values inspected |
| PostgreSQL identity/membership/bootstrap/temporal/security regressions | **NOT RUN** in continuation; no test cluster initialized |
| Actual mTLS and end-to-end onboarding/restart/denial/concurrency smoke | **NOT RUN**; certificate trust prerequisites unavailable |
| Ruff/formatter/Pyright on modified Python paths | Not applicable; no Python paths changed |
| Repository-wide diagnostics | Not run; no repository-wide success claim |

Previous checkpoint evidence, not a new continuation result: `uv sync --frozen` succeeded using Python 3.12.14; `uv run --frozen pytest -o addopts='' tests/architecture/test_pr2_00_boundaries.py -q` produced 3 passed in 2.29s, exit 0. That result does not demonstrate real authentication.

## Issues, backup and readiness

P0: none identified by this bounded inspection; no independent M1 security review performed.
P1: operational certificate trust prerequisites are unavailable in the inspected deployment configuration, blocking completion under the explicit continuation STOP rule. The former first-owner architecture blocker is resolved by M1-AUTH-001.
P2: M0 cancellation response-reuse metadata mismatch remains deferred (`literature_search_execution.py:1408/1534` at the M0 baseline). Its trust boundary was not modified. Historical repository-wide diagnostics remain unassessed.

All remaining M1 implementation and acceptance checks await the certificate prerequisites. M2 live literature search readiness: **NO**. No OpenAlex/Crossref implementation, push, merge, scientific data mutation or new worktree occurred. A local Git bundle is created and verified after this report commit, preserving the blocked continuation checkpoint rather than claiming completed M1 functionality.
