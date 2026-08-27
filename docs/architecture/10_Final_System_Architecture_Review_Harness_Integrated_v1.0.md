# ResearchBase Final System Architecture Review — Harness-Integrated v1.0

**Review mode:** adversarial / implementation-readiness / cross-phase consistency  
**Reviewed set:** System Architecture v1.3 + Phase 1 v1.2 + Phase 2 v1.1 + Phase 3 v1.1 + Phase 4 v1.1 + Cross-Phase Contract v1.1 + Harness Integration Specification v1.0

---

## 1. Executive verdict

**GO for design freeze. NO GO for unconstrained implementation.**

The Harness integration does not require reopening the canonical scientific architecture. The updated design preserves the strongest original properties:

- deterministic facts remain above review/approval;
- frozen provenance remains authoritative;
- Human and Agent use the same Application boundary;
- external research-agent frameworks remain replaceable;
- Phase 1 remains a provenance MVP, not an autonomous scientist;
- Agent Runtime activation remains Phase 3;
- failed/negative autonomous branches remain auditable.

After adversarial review, **no P0 or P1 architecture blocker remains in the integrated design**.

The main residual risk is no longer conceptual architecture. It is implementation discipline: developers must not mistake repository-level coding harness files in Phase 1 for permission to implement Phase-3 product runtime.

---

## 2. Attack surface reviewed

The review explicitly attacked:

```text
canonical-state pollution
Phase leakage
Skill explosion
instruction conflicts
harness supply chain
hidden direct DB writes
Agent self-modification
Reviewer pseudo-independence
STORM/EvoScientist coupling
unversioned behavior changes
false completion claims
MCP/tool output promoted as evidence
```

---

## 3. P0 findings

**None.**

No integrated rule currently permits an Agent/Skill/Plugin to redefine deterministic scientific truth, bypass Frozen Provenance Closure, or directly own canonical research state.

---

## 4. P1 findings

**None after incorporated corrections.**

Two candidate P1 issues were discovered during integration and corrected before freeze:

### Closed P1-A — HarnessFingerprint schema creep

Risk: introducing `HarnessFingerprint` as a new canonical entity would violate the existing Architecture Complexity Budget and prematurely expand Phase 1/3 schema.

Correction: it is explicitly a value/manifest by default. Phase 1 keeps it as PR evidence. Phase 3 binds it through existing AgentExecution/ArtifactVersion/value-object mechanisms; only an ADR may justify a minimal schema change.

**Status: CLOSED.**

### Closed P1-B — Phase-1 Agent Runtime leakage

Risk: adding `skills/`, routing policy and Codex harness could be misread as permission to implement a product SkillRouter/CapabilityGateway in Phase 1.

Correction: Phase 1 authorizes engineering-development harness only; generic product routing/runtime remains Phase 3. Phase 2 allows bounded scientific strategies without the generic router.

**Status: CLOSED.**

---

## 5. P2 residual findings

### P2-01 — External harness API drift

Third-party Skill/Plugin formats can evolve. A pinned revision gives reproducibility but does not guarantee future Codex runtime compatibility.

Required action:

```text
external harness upgrade
→ compatibility smoke test
→ harness regression
→ lock update
```

Do not assume immutable upstream content is automatically compatible with a newer runtime.

### P2-02 — Skill registry duplication risk

`SKILL.md` and `skill_registry.yaml` can drift into two conflicting declarations.

Required implementation rule:

> One field set must be authoritative and the other generated/validated.

Recommended choice: Skill-local metadata is authoritative for identity/purpose; central registry is authoritative for ResearchBase policy overlays (phase/capability/approval status). CI must reject contradictory duplicated fields.

### P2-03 — Reviewer independence can become cosmetic

Using a new subagent is insufficient if the reviewer receives an author-written summary that omits inconvenient facts.

Required action: `ReviewerContextBuilder` must build from authoritative spec, repository diff/artifacts, test evidence and canonical queries, not only from author-generated narration.

### P2-04 — Harness fingerprint completeness is runtime-dependent

Model/provider/runtime may not expose every immutable identifier. Treat missing fields explicitly as `unknown/unavailable`, not silently as reproducible.

Required action: fingerprint completeness must be reported as a quality field, and formal reproducibility claims must state limitations.

---

## 6. P3 recommendations

### P3-01 — Do not install every available Skill

Keep the ResearchBase-owned set small. Expand by strategy/reference first.

### P3-02 — Prefer wrappers over forks

For mature engineering harnesses, prefer pinned external dependency + ResearchBase policy wrapper. Fork only when upstream behavior fundamentally conflicts with ResearchBase boundaries.

### P3-03 — Maintain a harness compatibility matrix

Track:

```text
Codex runtime
external harness revision
plugin revision
ResearchBase revision
status
```

This will reduce upgrade uncertainty.

---

## 7. Internal-logic consistency review

### 7.1 Canonical scientific state

**PASS.**

Harness constructs are not allowed to become a second source of scientific truth.

### 7.2 Human / Agent boundary

**PASS.**

Both continue to converge on Application Command/Query.

### 7.3 Phase 1 scope

**PASS.**

Engineering harness is a development mechanism, not product Agent Runtime.

### 7.4 Phase 2 scientific strategies

**PASS.**

STORM is correctly placed as a replaceable strategy underneath a stable literature-research responsibility.

### 7.5 Phase 3 Agent Runtime

**PASS.**

Routing, capability policy, Candidate Promotion, AgentExecution provenance and reviewer independence are placed in the correct phase.

### 7.6 Phase 4 evolution

**PASS.**

Self-evolution is candidate → eval → governed release, not live self-rewrite.

### 7.7 Cross-phase compatibility

**PASS.**

Later phases extend rather than reinterpret earlier canonical semantics.

---

## 8. “Can intermediate programmers build this?” review

### Phase 1

**YES**, with low ambiguity.

The developer can follow PR-scoped work, concrete tests and evidence packages without understanding STORM/EvoScientist internals.

### Phase 2

**YES**, provided each scientific Skill gets a separate implementation spec/acceptance fixture when its PR begins.

The important improvement is that developers no longer need to “read STORM and infer how ResearchBase should use it.” They implement the `literature-deep-research` contract and one named strategy adapter.

### Phase 3

**YES, but Tech Lead ownership remains required** for:

```text
SkillRouter
CapabilityPolicy
AgentExecution provenance
Candidate Promotion
HarnessFingerprint persistence mapping
sandbox/security boundary
```

These are architecture-sensitive and should not be delegated as independent loosely coordinated tickets.

### Phase 4

**YES only after Phase-3 contracts have proven stable.**

Do not parallelize self-evolving Skill work before the evaluation/release pipeline itself is trustworthy.

---

## 9. STORM / EvoScientist comprehensibility test

The previous documentation risk was real: a developer could see a reference to STORM/EvoScientist without knowing whether to fork, embed, copy schema or merely borrow methodology.

The integrated documentation now makes the decision explicit:

```text
STORM
→ literature-deep-research strategy
→ Phase 2 native strategy first
→ optional thin adapter
→ no canonical STORM schema

EvoScientist
→ Phase-3 orchestration reference/adapter candidate
→ compare with native ResearchBase orchestration
→ never own canonical research state
```

**PASS.**

---

## 10. Harness conflict test

Potential conflict:

```text
external Skill says "do X"
ResearchBase Phase says "do not X"
```

The new precedence contract resolves this deterministically in favor of ResearchBase invariants/Phase spec.

**PASS.**

---

## 11. Reproducibility test

The integrated design now recognizes four reproducibility dimensions:

```text
Data
Code/Artifact
Environment
Agent Harness
```

This is stronger than ordinary “prompt logging” because the effective Skill/Plugin/routing revisions are versioned.

**PASS with P2-04 limitation:** runtime identifiers may occasionally be unavailable and must be recorded as such.

---

## 12. Security review

The new design avoids the most dangerous harness failure modes:

```text
unreviewed external Skill
unbounded MCP trust
direct DB mutation
Agent approval escalation
silent self-modification
hidden Hook mutation
```

**PASS at architecture level.**

Implementation still requires real sandbox and capability tests in Phase 3.

---

## 13. Complexity-budget review

The integration adds configuration/runtime concepts but no mandatory new top-level scientific entity.

The bounded 12-Skill initial registry also prevents a “one tiny prompt = one Skill” explosion.

**PASS.**

---

## 14. Required freeze corrections before code

The following are considered part of this review decision and should be applied during repository bootstrap/Phase implementation:

1. central Skill registry must not duplicate Skill metadata without validation;
2. ReviewerContextBuilder must source evidence independently;
3. HarnessFingerprint must expose completeness/unknown fields;
4. external harness upgrades require compatibility + regression checks.

These are P2 implementation requirements, not design blockers.

---

## 15. Final score

| Dimension | Score |
|---|---:|
| Internal logical consistency | 9.6 / 10 |
| Canonical-state discipline | 9.8 / 10 |
| Cross-phase compatibility | 9.6 / 10 |
| Implementation clarity | 9.3 / 10 |
| Agent/harness replaceability | 9.7 / 10 |
| Scientific reproducibility | 9.6 / 10 |
| Security boundary design | 9.3 / 10 |
| Complexity control | 9.5 / 10 |

**Overall: 9.55 / 10 — DESIGN FREEZE RECOMMENDED.**

---

## 16. Final decision

```text
System Architecture v1.3         FROZEN
Phase 1 Spec v1.2                FROZEN
Phase 2 Spec v1.1                FROZEN
Phase 3 Spec v1.1                FROZEN
Phase 4 Spec v1.1                FROZEN
Cross-Phase Contract v1.1        FROZEN
Harness Integration Spec v1.0    FROZEN

P0 OPEN                           0
P1 OPEN                           0
P2 TRACKED                        4

Implementation                   NOT STARTED
```

The next legitimate transition is not another architecture redesign. It is **Phase 1 GO**, followed by PR-scoped implementation under the frozen architecture and engineering harness.

---

## 17. Final principle

> **Documents define the system. The harness constrains how agents build and operate it. Canonical provenance determines what is scientifically true.**
