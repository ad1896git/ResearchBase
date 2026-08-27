# ResearchBase Harness Integration Specification v1.0

**Status:** FROZEN FOR IMPLEMENTATION REVIEW  
**Scope:** Engineering Harness + Scientific Skills + Phase-3 Harness Runtime  
**Canonical scientific schema:** unchanged by this specification

---

## 1. Purpose

This specification turns the Harness Integration Architecture into an implementable contract for Codex and human developers.

It answers five implementation questions:

1. Which parts are external dependencies and which are ResearchBase-owned?
2. Where are Skills, strategies, policies and evaluations stored?
3. How is a Skill selected and what can it access?
4. How is harness behavior versioned and reproduced?
5. At which Phase may each runtime capability become active?

The specification intentionally does **not** define a second research object model.

---

## 2. Non-negotiable boundary

```text
Harness / Agent / Skill / Plugin
             ↓
       Application API
             ↓
       ResearchBase Core
             ↓
      Repository / UoW
             ↓
         PostgreSQL
```

Forbidden:

```text
Skill → direct ORM mutation
Plugin → direct SQL canonical write
Hook → hidden scientific-state mutation
MCP → canonical evidence by assertion
Agent review → scientific truth
```

---

## 3. Ownership matrix

| Capability | Owner | Phase | Strategy |
|---|---|---:|---|
| Coding workflow | external engineering harness | 1+ development | reuse/pin |
| TDD/debug/review | external engineering harness | 1+ development | reuse/pin |
| Security review | approved external plugin | 1+ development / later runtime | reuse/pin |
| Skill evaluation tooling | external + ResearchBase evals | 1+ | reuse + own benchmarks |
| Literature research | ResearchBase | 2+ | own Skill, pluggable strategy |
| Scientific auditing | ResearchBase | 2/3+ | own Skills |
| Generic Skill routing | ResearchBase runtime | 3+ | implement |
| Capability policy | ResearchBase runtime | 3+ | implement |
| Harness fingerprint binding | ResearchBase runtime | 3+ | implement |
| Dynamic Skill evolution | ResearchBase | 4+ | governed candidates only |

---

## 4. Repository layout

```text
ResearchBase/
├── AGENTS.md
├── harness.lock.yaml
├── .codex/
│   └── config.toml
│
├── config/harness/
│   ├── skill_registry.yaml
│   ├── routing_policy.yaml
│   └── capability_policy.yaml
│
├── docs/harness/
│   ├── harness_architecture.md
│   ├── skill_authoring_standard.md
│   ├── harness_eval_protocol.md
│   └── external_dependency_review.md
│
├── skills/
│   ├── research-question-refiner/
│   ├── literature-deep-research/
│   ├── literature-evidence-auditor/
│   ├── hypothesis-auditor/
│   ├── experiment-designer/
│   ├── experiment-protocol-auditor/
│   ├── statistical-auditor/
│   ├── result-claim-auditor/
│   ├── reproducibility-auditor/
│   ├── citation-auditor/
│   ├── paper-auditor/
│   └── research-architecture-auditor/
│
├── references/research-methods/
│   ├── STORM/
│   ├── EvoScientist/
│   ├── PaperQA2/
│   └── scientific-method/
│
├── evals/
│   ├── skills/
│   ├── routing/
│   └── regression/
│
└── pr_evidence/
```

Phase 1 may create the engineering-governance skeleton. Product runtime wiring for `skill_registry`, routing and capability enforcement begins only where the relevant Phase specification allows it.

---

## 5. `harness.lock.yaml` contract

Purpose: reproducible external harness resolution.

Minimum conceptual schema:

```yaml
schema_version: 1

external_harnesses:
  - id: superpowers
    source: obra/superpowers
    revision: <immutable-tag-or-commit>
    license: <resolved-license>
    approved_for:
      - engineering-development

  - id: agent-skills
    source: addyosmani/agent-skills
    revision: <immutable-commit>
    license: <resolved-license>
    approved_for:
      - engineering-development

official_plugins:
  - id: codex-security
    source: openai/plugins
    revision: <immutable-revision>

  - id: plugin-eval
    source: openai/plugins
    revision: <immutable-revision>
```

Rules:

- Never pin `latest`, `main` or `master` as the reproducibility identity.
- Network URL is not a version.
- Updating a resolved revision is a harness behavior change and requires regression evidence.
- Lock entries do not grant capabilities by themselves.

---

## 6. Skill package standard

ResearchBase-owned Skill:

```text
skills/<skill-id>/
├── SKILL.md
├── references/
├── strategies/
├── scripts/
└── evals/
```

`SKILL.md` MUST define:

```text
identity
purpose
trigger conditions
non-trigger conditions
required inputs
allowed outputs
canonical-state rules
capabilities required
capabilities forbidden
verification steps
stop conditions
failure behavior
```

A Skill MUST NOT rely on hidden knowledge for a method that can be explicitly referenced.

---

## 7. Initial Skill registry

```text
RB-S01 research-question-refiner
RB-S02 literature-deep-research
RB-S03 literature-evidence-auditor
RB-S04 hypothesis-auditor
RB-S05 experiment-designer
RB-S06 experiment-protocol-auditor
RB-S07 statistical-auditor
RB-S08 result-claim-auditor
RB-S09 reproducibility-auditor
RB-S10 citation-auditor
RB-S11 paper-auditor
RB-S12 research-architecture-auditor
```

No additional top-level Skill should be added unless a Skill Boundary Review shows that an existing Skill + strategy/reference cannot express the responsibility without trigger ambiguity or contradictory capability requirements.

---

## 8. `skill_registry.yaml` conceptual schema

```yaml
skills:
  - skill_id: RB-S06
    name: experiment-protocol-auditor
    version: 1.0.0
    owner: researchbase
    category: scientific-audit

    allowed_phases: [2, 3, 4]

    triggers:
      - experiment protocol validation
      - leakage audit
      - split/seed/baseline audit

    outputs:
      - candidate_audit_report
      - candidate_findings

    capabilities:
      allow:
        - canonical_query
        - artifact_read
      deny:
        - canonical_direct_write
        - approval
        - external_publish
        - harness_modify

    independent_execution: true
    verification_profile: scientific_auditor_v1
```

This registry is repository configuration, not canonical scientific truth.

---

## 9. Strategy contract

Skill and strategy are distinct.

```text
Skill = stable responsibility / trigger / safety contract
Strategy = replaceable way of performing that responsibility
```

Example:

```text
RB-S02 literature-deep-research
├── baseline-multisource
├── STORM-like
├── Co-STORM-like
└── future strategy
```

Strategy selection MUST NOT alter LiteratureSource, SourceVersion or LiteratureEvidence semantics.

---

## 10. STORM integration contract

STORM is treated as:

```text
METHOD_REFERENCE in design
→ native strategy implementation in Phase 2
→ optional thin external adapter if useful
```

STORM-derived intermediate structures may exist as transient working state or execution artifacts. They MUST NOT become new canonical scientific entity types merely because upstream STORM uses them.

The formal output enters ResearchBase only through existing literature/evidence Application APIs.

---

## 11. EvoScientist integration contract

EvoScientist is treated as an orchestration/runtime reference.

Phase 3 may compare:

```text
ResearchBase-native orchestration
vs
thin EvoScientist-like service adapter
```

Acceptance criterion:

> The adapter can be replaced without migrating canonical scientific state.

External orchestration state is never the authoritative Hypothesis, ExperimentSpec, Run, Measurement, Claim or ScientificConclusion state.

---

## 12. Routing policy

Runtime routing begins in Phase 3.

Algorithm contract:

```text
1. classify task intent
2. identify current Phase/workflow state
3. resolve actor authority
4. resolve data/capability constraints
5. retrieve eligible Skills
6. detect Skill conflicts
7. apply precedence
8. produce execution plan
9. execute
10. verify/promote/stop
```

The router MUST be deterministic for hard policy exclusions even when ranking among otherwise eligible Skills is model-assisted.

---

## 13. Instruction precedence

```text
1. ResearchBase architecture/safety invariants
2. Scientific integrity rules
3. Current Phase specification
4. Repository AGENTS.md
5. ResearchBase-owned Skill
6. Approved external engineering harness
7. Generic agent preference
```

A lower layer cannot weaken a higher layer.

Unresolvable conflict:

```text
STOP
→ record Architecture/Engineering Question
→ no canonical mutation
```

---

## 14. Capability policy

Capabilities are granted by task/role/phase, not by Skill popularity or model request.

Example profiles:

### `scientific_auditor_v1`

Allowed:

```text
canonical query
artifact read
source retrieval
candidate finding creation
```

Forbidden:

```text
direct DB write
approval
external submission
harness modification
historical fact mutation
```

### `coding_agent_phase1_v1`

Allowed:

```text
repository read/write within target PR
local test execution
approved dependency tooling
PR evidence generation
```

Forbidden:

```text
product Agent Runtime implementation unless target PR explicitly authorizes it
production canonical DB mutation
schema expansion without ADR
later-PR implementation
```

---

## 15. Candidate Promotion

Every scientific generative Skill defaults to candidate output.

```text
candidate
→ validation/audit
→ explicit Application Command
→ canonical state
```

No prompt wording such as “final”, “approved” or “high confidence” changes this boundary.

---

## 16. Independent review contract

Reviewer input SHOULD include:

```text
authoritative requirements
relevant canonical state
candidate artifact/diff
machine verification evidence
known constraints
```

Reviewer input SHOULD NOT require the author's full hidden/working reasoning history.

Formal review finding schema:

```text
finding_id
severity: P0|P1|P2|P3
category
target/location
observation
evidence
violated_rule_or_risk
impact
recommended_action
confidence
```

---

## 17. HarnessFingerprint

`HarnessFingerprint` is a **value/manifest**, not a new top-level canonical entity by default.

Conceptual content:

```json
{
  "researchbase_revision": "...",
  "agent_runtime_revision": "...",
  "model_identifier": "...",
  "agents_md_sha256": "...",
  "config_sha256": "...",
  "skills": [
    {"id": "RB-S06", "version": "1.0.0", "content_sha256": "..."}
  ],
  "plugins": [],
  "hooks": [],
  "mcp_capabilities": [],
  "external_harnesses": []
}
```

Persistence rule:

- Phase 1: PR/development evidence only.
- Phase 2: strategy/Skill revisions used to produce material literature artifacts must be identifiable in execution/artifact provenance where applicable, without inventing a generic AgentExecution subsystem early.
- Phase 3+: bind the resolved fingerprint to AgentExecution provenance using existing AgentExecution/ArtifactVersion/value-object mechanisms.
- If these mechanisms prove insufficient, an ADR must justify the smallest schema change. Creating a new top-level canonical `HarnessFingerprint` entity is **not** the default.

---

## 18. Engineering Harness workflow

For material implementation PRs:

```text
SPEC
→ PLAN
→ IMPLEMENT IN SCOPE
→ TEST
→ INDEPENDENT REVIEW
→ ARCHITECTURE CHECK
→ VERIFY
→ EVIDENCE PACKAGE
→ STOP
```

A PR is not complete because the agent says it is complete.

---

## 19. Completion evidence

At least the checks required by the PR/Phase specification must have concrete evidence.

Examples:

```text
pytest result
PostgreSQL integration result
clean migration result
architecture tests
lint/typecheck
OpenAPI smoke test
E2E/failure injection output
```

Skipped checks must be explicitly reported as skipped with reason; they MUST NOT be described as passing.

---

## 20. Skill evaluation protocol

Every ResearchBase Skill release must include:

### Trigger suite

- positive cases
- negative cases
- ambiguous cases

### Behavior suite

- normal evidence
- insufficient evidence
- conflicting evidence
- malformed inputs
- adversarial prompt/tool content

### Safety suite

- denied capability request
- attempted direct canonical write
- attempted approval escalation
- attempted harness modification

### Quality suite

- false-positive audit cases
- false-negative audit cases
- output-schema conformance
- evidence traceability

### Regression suite

Compare against the previous released Skill/strategy version.

---

## 21. Harness change classification

### HC-0 Documentation-only

No executable instruction/routing/capability behavior change.

### HC-1 Skill wording/reference change

Requires trigger/behavior regression.

### HC-2 Routing/capability/hook change

Requires full harness regression + security/capability review.

### HC-3 Canonical boundary impact

Requires ADR + architecture review + relevant migration/contract tests.

---

## 22. Third-party dependency intake

Before approval:

```text
identify authoritative repository
resolve immutable revision
review license
review instructions
review scripts
review Hooks/MCP/tool permissions
run relevant evals
record approval scope
pin revision
```

Stars/popularity are discovery signals, not trust evidence.

---

## 23. Self-modification rule

A running agent cannot modify and immediately trust:

```text
AGENTS.md
production Skill
routing policy
capability policy
harness.lock
required auditor definition
```

Such changes become candidate engineering changes and require a new governed execution after evaluation/release.

---

## 24. Phase activation matrix

| Capability | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|
| engineering harness for coding | YES | YES | YES | YES |
| Skill authoring/evals as repo assets | MAY | YES | YES | YES |
| literature scientific strategies | NO product runtime | YES | YES | YES |
| generic Skill Router | NO | NO | YES | YES |
| CapabilityPolicy runtime | NO | bounded per-service only | YES | YES |
| AgentExecution harness binding | NO | NO generic runtime | YES | YES |
| dynamic Skill composition | NO | NO | bounded | YES |
| self-evolving candidate Skills | NO | NO | NO | YES governed |

---

## 25. Phase-1 implementation checklist

Phase 1 may implement only the **development harness bootstrap**:

```text
[ ] AGENTS.md
[ ] harness.lock.yaml
[ ] engineering harness intake record
[ ] PR evidence convention
[ ] harness change/regression CI where practical
```

Do **not** implement:

```text
[ ] SkillRouter product service
[ ] CapabilityGateway product runtime
[ ] AgentExecution product orchestration
[ ] STORM runtime integration
[ ] EvoScientist adapter
[ ] autonomous research loop
```

---

## 26. Phase-2 implementation checklist

```text
[ ] RB-S02 literature-deep-research contract
[ ] baseline literature strategy
[ ] STORM-like native strategy
[ ] source verification/evidence promotion
[ ] PaperQA2 adapter contract if selected
[ ] RB-S03 literature-evidence-auditor
[ ] RB-S10 citation-auditor
[ ] Skill/strategy eval fixtures
```

All canonical writes use existing Application APIs.

---

## 27. Phase-3 implementation checklist

```text
[ ] SkillRegistryLoader
[ ] SkillRouter
[ ] RoutingPolicy
[ ] CapabilityPolicy
[ ] HarnessResolver
[ ] HarnessFingerprintBuilder
[ ] AgentExecution binding
[ ] ReviewerContextBuilder
[ ] independent audit executions
[ ] supply-chain enforcement
[ ] self-modification guard
[ ] crash/recovery tests
[ ] prompt/tool injection tests
```

---

## 28. Phase-4 implementation checklist

```text
[ ] dynamic strategy ranking
[ ] controlled Skill composition
[ ] Candidate Skill evolution
[ ] eval/benchmark promotion gate
[ ] cross-project package isolation
[ ] long-horizon harness provenance
```

---

## 29. Required architecture tests

At minimum by the appropriate Phase:

```text
test_harness_cannot_write_db_directly
test_external_harness_dependencies_are_pinned
test_researchbase_invariants_override_external_skill
test_skill_router_respects_phase
test_skill_router_respects_capability_policy
test_scientific_skill_output_is_candidate_by_default
test_auditor_cannot_approve
test_auditor_cannot_direct_write
test_reviewer_context_is_independently_reconstructed
test_harness_fingerprint_is_reconstructable
test_running_agent_cannot_self_weaken_harness
test_storm_not_in_core_schema
test_evoscientist_not_in_core_schema
test_external_tool_output_not_automatically_evidence
```

---

## 30. Definition of Done for a production Skill

A Skill is released only when:

1. responsibility/trigger is non-overlapping enough to route reliably;
2. capability allow/deny policy is explicit;
3. output is typed/candidate-scoped;
4. stop/failure behavior is defined;
5. references/strategies are version-controlled;
6. positive and negative trigger evals pass;
7. adversarial/safety evals pass;
8. behavior regression is acceptable;
9. independent review has no P0/P1 finding;
10. release version/content digest is recorded.

---

## 31. Implementation instruction to Codex

When implementing this specification:

```text
Do not interpret this document as permission to implement later phases.
Follow the current Phase specification first.
Do not create new canonical scientific entities for Skill/Plugin/Harness concepts unless an ADR proves the existing model insufficient.
Do not wire third-party harnesses directly to persistence.
Do not treat tool output as scientific evidence without owning-domain validation.
Do not bypass Candidate Promotion.
Do not modify the production harness during the same trusted execution.
Provide concrete verification evidence before claiming completion.
STOP at the named PR/Phase gate.
```

---

## 32. Final design principle

> **The Harness controls agent behavior; ResearchBase controls scientific truth.**

> **External engineering intelligence is replaceable. Scientific methodology is explicitly owned, evaluated and versioned.**
