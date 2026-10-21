# ADR-0021 — TDG-3 Phase 3 technology decisions

Status: ACCEPTED — APPROVED by owner 2026-10-20 ("全部按推荐": all recommended options).
Only PR3-00 is authorized for implementation.

## Context

[TDG-3 draft](../../proposals/TDG3_Phase3_Technology_Decision_Gate_DRAFT.md) lists the
fourteen Phase 3 technology decisions with options, intake obligations and dependent PRs.
Phase 2 was accepted on 2026-10-20 ([acceptance record](../../phase2/phase2_acceptance_2026-10-20.md)).

## Decision

| ID | Decision |
|---|---|
| TDG3-01 | Phase 3 GO. First authorized PR: **PR3-00 only**. Every later PR needs its own authorization. |
| TDG3-02 | DEV_LOCAL; dedicated isolated CPU execution; no GPU or cloud/HPC credentials. |
| TDG3-03 | Constrained Docker sandbox (no network, host home/socket mounts, privileged mode or secrets by default; CPU/memory/disk/process/time limits), subject to host, license and containment intake before PR3-06 activates it. |
| TDG3-04 | Small native state machine; no external agent runtime framework owns task or scientific state. |
| TDG3-05 | PostgreSQL-backed dispatch, leases and idempotency; no Redis or separate broker. |
| TDG3-06 | One API-based primary coding adapter for PR3-09, provider named by the owner at intake; PR3-10 alternate recorded as an explicit SHOULD deferral; fake adapter retained. Subscription quotas (development-pipeline CLIs) are not product adapters (owner rule 2026-10-19). |
| TDG3-07 | One API-based model profile named by the owner at intake; pilots use synthetic/test fixtures only; API credentials held by the owner outside agent workspaces, prompts, artifacts and logs. Until a provider is named, only fake adapters run. |
| TDG3-08 | A1/A2 default; human ExperimentSpec/Claim freeze and formal release; A3 only under a separately authorized bounded policy; no A4, self-approval or external venue send. |
| TDG3-09 | Pilot caps per task: 30 min, 50 agent steps, 50 model calls, 20 search calls, 3 code iterations, 5 Runs, 10 nodes, depth 3, 1 parallel branch, 0 GPU hours, USD 5 equivalent token cost. No agent-raised limit. |
| TDG3-10 | Hard stop on the first exhausted bound; stop after 2 repeated failures or 2 no-improvement iterations; only an explicit human approval grants a new budget; history retained. |
| TDG3-11 | Schema only in the owning PR, registry/pattern-based; atomic typed promotion in the same transaction as the canonical write; migrations merged serially with one head. |
| TDG3-12 | Skills/tools only through the existing bounded registry; each executable revision reviewed and pinned; reference-only libraries stay references. |
| TDG3-13 | Zero direct-write, self-approval, closure, isolation, history-deletion and hard-budget violations; quality/cost/recovery targets frozen on fixed fixtures before PR3-20. |
| TDG3-14 | Owner eshine owns gates, budgets and incidents; the director (Claude Code, under owner delegation) is independent reviewer and first reviewer for migrations and security; the owner may override. |

## Consequences

Each external dependency still needs intake (exact revision, license/terms, transitive
dependencies, data exposure, rollback) in its owning PR before activation. Items 06/07 stay
on fake adapters until the owner names a provider; PR3-00..PR3-08 do not need one.
