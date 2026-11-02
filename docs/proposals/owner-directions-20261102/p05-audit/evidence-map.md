PROPOSED / NON-NORMATIVE / NO IMPLEMENTATION AUTHORITY

Source baseline: `7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2`. This is the P05 docs-only preparation child, not a scientific contract freeze, architecture change, executable packet, facility authorization or whole-P05 completion. Parent risk stays HIGH. OBSERVED_SOURCE means inspected static code; HISTORICAL_ACCEPTANCE means a cited acceptance record, not a new test. All proposed behavior below is PROPOSED. Environment, actual backend and independent review are UNVERIFIED/UNASSIGNED_OWNER_INPUT.

# Evidence map and unresolved dependency binding

All paths below are relative to the frozen repository baseline; `AR` abbreviates `src/researchbase/agent_runtime`. Source references identify static facts only.

| Classification | Exact source/heading | Observed fact and limitation |
| --- | --- | --- |
| OBSERVED_SOURCE | `AGENTS.md` §§3–6,9–11 | Owning canonical facts, Application transaction boundary, real PG18 testing and evidence-before-PASS govern later work. |
| OBSERVED_SOURCE | `docs/architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md` §2 invariants; architecture02 correction and architecture03 registry | Canonical history/provenance and owning schemas take priority over runtime convenience; draft storage is not architecture. |
| OBSERVED_SOURCE | `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md` invariants | ExperimentSpec, Run, review/approval and derived memory remain distinct. |
| HISTORICAL_ACCEPTANCE | `docs/architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md` Decision TDG3-03/05/07/11 | Native PostgreSQL dispatch direction, restricted container intake, fake-until-provider and owning schema gates; every PR still needs authorization. |
| OBSERVED_SOURCE | `docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md` §§25,45–49; PR3-19 | Recovery taxonomy, transactional dispatch, reclaim/idempotency and timeout≠failure requirements; no delivered dispatcher inferred. |
| OBSERVED_SOURCE | `AR/domain/research_task.py`; `AR/domain/task_step.py:25–45`; `AR/application/research_task.py` | Existing planning/task/step ownership; display/progress states are not admitted execution authority. |
| OBSERVED_SOURCE | `AR/application/agent_executions.py:1,198–218,289–325`; `AR/application/execution_contracts.py:14–107` | CREATED intent, exact request material and replay exist. No actual running producer/promotion is attested. |
| HISTORICAL_ACCEPTANCE | `docs/phase3/PR3-02-S2-contract-freeze.md` §1/Q1; `PR3-02-S2-intent-evidence.md` | Intent-only slice explicitly excludes lifecycle transitions/work. Evidence remains historical, not a fresh test. |
| OBSERVED_SOURCE | `AR/application/gateway_contracts.py:50–110,255–298`; `AR/application/capability_gateway.py:391–467` | Closed fake request/context; committed fresh start authorizes finite fake call; unresolved replay refuses redispatch. Not real backend/lease/worker support. |
| OBSERVED_SOURCE | `AR/application/capability_gateway.py:127–217,469` | Gateway accounting and immutable saved completion are existing seams. A future dispatch contract must preserve these owners. |
| OBSERVED_SOURCE | `AR/application/task_safety.py:238–277,641–673`; `AR/application/safety_contracts.py:255–300` | Fake consumer trust, current owner checks, command commit/replay, reservation/settlement values. No production consumer capability inferred. |
| HISTORICAL_ACCEPTANCE | `docs/phase3/PR3-03-contract-freeze.md` §1; `PR3-03-evidence.md` | Accepted-direction narrative plus delivered gateway evidence must be distinguished from historical PACK DRAFT header. Explicit real queue/lease/provider exclusions remain. |
| HISTORICAL_ACCEPTANCE | `docs/phase3/PR3-04-acceptance.md` Result/Not in this acceptance; `PR3-04-contract-freeze.md` | Budget groundwork accepted conditionally on exact CI; no S2 execution or full memory save acceptance inferred. |
| HISTORICAL_ACCEPTANCE | `docs/phase3/PR3-05-readonly-acceptance.md` Owner decisions/Not included | Read-only reconstruction accepted; durable save and save-lock protocol deferred. Dispatch planning cannot enable them. |
| OBSERVED_SOURCE | `docs/harness/09_Harness_Integration_Specification_v1.0.md` forbidden direct-write/Phase3 runtime rules | External Harness/engineering ledgers do not own canonical scientific persistence or grant product adapter authority. |
| PROPOSED | `dispatch-contract-draft.md` §§1–8 | Closed conceptual request/result, timeline/fence/unknown/accounting/dependency proposal, not implemented or frozen. |
| UNVERIFIED/UNASSIGNED_OWNER_INPUT | `dispatch-contract-draft.md` §§7–8 | Linux host/image/bounds/budget/credentials, P06 backend key/receipt guarantees and exact source/PG scope absent. |

## P01 and engineering admission dependencies

The external reviewed control package is not repository architecture. Its prepared `approved-20261102/completions/P01.json` and `P01-scope-continuity.json` bind whole-P01 **audit** only. The reviewed source-manifest and frozen P05 contract identify their exact bytes; this child neither installs, rewrites nor creates a completion receipt. A host must independently validate their exact frozen references, original audit report and reviews at actual admission. The recent duplicate BACKLOG annotation/restoration history is not permission to ignore future drift.

The approved execution specification and exact contract are operator-supplied packet inputs, not hidden repository dependencies. This worktree does not fabricate portable owner authorization or a P01 machine gate. Successful reviewed54 runtime deployment, matching live P01 binding and reviewed docs-index installation are still required before automatic admission. At preparation time live remained47 and54 deployment was STOPPED after a preflight isolation failure; no child dispatch/runtime success is claimed.

## Coverage boundaries

No fresh PG, provider, compute, kernel sandbox, lifecycle, crash/recovery or result-ingestion experiment was run. Source presence and historical acceptance do not prove those results. Existing Application ownership must not be rebuilt as a second service. Exact operation/schema/interface choices and bytes still need independent contract review, owning source authorization and facilities. The acceptance-plan names future tests; it is not their evidence.
