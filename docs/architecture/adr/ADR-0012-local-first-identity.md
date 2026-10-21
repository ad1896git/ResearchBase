# ADR-0012 — M1-AUTH-002: Local-first identity

Status: approved by architecture owner, 2026-10-10.

The MVP is a single-user local research workbench, operated from a terminal or SSH under the same trusted macOS/Linux account. CLI authentication uses kernel process credentials, never a username, environment identity, actor flag or HTTP header. Real and effective UID/GID must agree; root and setuid/setgid invocation are refused. A protected installation configuration binds the UID to a host identifier and random installation identifier; canonical actor resolution uses the existing deployment/OS_UID subject binding and its credential ID. Missing mapping never creates an Owner.

First use initializes owner-only operational files outside the checkout, then uses the existing atomic first-owner Application ceremony, one-use bootstrap secret and retained authenticated audit proof. PostgreSQL owns Actor, binding, Project, membership and role. No schema is added. Local credential validity is deployment policy: the protected installation record must remain enabled, readable and valid at each fresh DB authorization time. Membership, role, retirement and binding revocation remain canonical checks.

CLI does not require mTLS. M1-AUTH-001 is inapplicable to this profile. Network HTTP retains its existing fail-closed authentication requirements; local operation starts no listener. Multi-user/network deployment requires a separately approved authentication profile.

The OS account, its configuration and its database credentials are trusted. HMAC-authenticated local audit records protect accidental alteration and establish integrity within this deployment trust boundary; they do not provide independent operator attestation or nonrepudiation against the account owner. A machine clone with a duplicated platform identifier is outside this local trust guarantee. Backup relocation requires explicit re-enrollment, not automatic UID remapping.

Untrusted Agent execution must run outside the trusted account/credential boundary and must not inherit unrestricted local-user or PostgreSQL privileges. This release supplies no Agent sandbox. Scientific history, hashes and Phase 1 service compatibility remain unchanged. Only authenticated local workbench commands and existing authorized literature commands are exposed by production CLI composition; remaining legacy CLI groups fail closed pending scoped integration.
