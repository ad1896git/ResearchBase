# PR2-06 conditional development slice: retained M3 provider gate

Baseline: accepted M3 Runner binding `0938f57edba0182b97ae99a3ac392eed3514f7ab`.

The frozen Phase 2 PR sequence names PR2-06 SearchCapability after PR2-05
LiteratureEvidence. The provider-neutral port, deterministic test adapter and
OpenAlex adapter already exist. TDG2 requires an upstream version/license/security
and access review before enabling a live adapter. This slice makes the **exact
retained M3 database** default-deny live OpenAlex registration until that
separate gate is met. It leaves all four accepted M2 deployments and disposable
databases on their existing composition path. It does not add another provider,
make a network call, change SearchCapability DTOs, or alter scientific state.

Acceptance: exact retained M3 composes without a live SearchCapability even when
an OpenAlex key is present; each M2 database still resolves its existing
OpenAlex version; unknown/disposable database names retain their prior behavior;
no schema, migration, HG1 identity or retained deployment file changes.

Status: conditional development only. M3 Human Gate and formal milestone
acceptance remain blocked. No external adapter activation approval is claimed.
