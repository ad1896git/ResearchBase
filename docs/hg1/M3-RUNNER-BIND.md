# Retained M3 Runner binding

The only new Runner profile is database `researchbase_m3_retained_20261011` over
the `/private/tmp` PostgreSQL Unix socket on port `55440`, installation
`/Users/onephone/ResearchBaseData/rb-m3-retained-installation`, and CAS
`/Users/onephone/ResearchBaseData/rb-m3-retained-artifacts`. The Runner checks
the PostgreSQL system identifier `7695048034454027996`, durable PGDATA, exact
M3 revision, and the HG1-00B peer/reject HBA rules before opening its socket.
The four M2 profiles retain their previous policy-optional behavior.

M3 requires `/Library/Application Support/ResearchBase/hg1-02-m3-retained.json`.
It is absent at candidate freeze. The trusted host administrator must separately
approve and install a root-owned policy, with every path parent root-owned and
not group/other writable. The policy file must be regular, non-symlinked,
single-linked, root-owned, and not group/other writable. There is no user-writable
fallback. Installation is a separate host action, not part of this change.

The exact JSON fields are `version: 1`, `deployment_id`, `operator_uid`,
`operator_public_key`, `operator_public_key_sha256`, `audit_root`, and `peers`.
There must be exactly three peer records for A, B and C, each with `uid`,
`actor_id`, `credential_id`, `not_before`, and `not_after`. The deployment ID,
A actor and credential must match the active canonical retained M3 installation.
`operator_uid` must be distinct from A's UID, and B must be distinct from both.
The operator public key must be a genuine, approved C credential; the audit root
must be a private direct child of
`/Users/onephone/ResearchBaseData/migration-evidence`. The existing HG1-02
policy parser and canonical binding checks reject missing or inconsistent data.
Do not fabricate B/C records to enable the Runner.

After separate administrator approval, install the policy atomically from an
administrator-controlled staging file under the same root-controlled directory,
with mode `0600`, root owner, and no symlink components. Verify its digest,
ownership, mode, exact fields and canonical credential bindings before starting
the Runner. Use the explicit approved M3 database URL and roots above. Perform
the read-only owner Runner smoke only after the installed policy passes these
checks. No real B/C enrollment or scientific review is implied.
