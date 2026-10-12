# PR2-15-S1 V5 shared implementation matrix and plan

Authority: frozen companion 20 v1.0, SHA-256 `e22b6b4f5f5a93863a3d1f3fe06e1ece4e4ed626b67feb6d0f93b50dec09d231`. Accepted engineering base `9b7aa8660c8d90bd2eaba20c747dba30bc2b949d`; exact seven authoritative/freeze documents restored from `aaea2d2c17e881d4256e6ecb74810eb9b92475ef`, not a design-branch merge. No normative text changes.

## Interface and contract-to-test matrix

| Clause | Shared interface/invariant | Verification |
| --- | --- | --- |
| §2,6 | `DecisionService(factory, credentials, literature_evidence).record_decision(principal, command)`; frozen dataclass `RecordDecisionCommand(id: UUID, project_id: UUID, scientific_conclusion_version_id: UUID, question: str, rationale: str, decision_type: str='INTERNAL_SCIENTIFIC_RELEASE', decision: str='PROCEED')` | Closed typed input, NFC text, trusted actor/time, reject unsupported fields/type/value |
| §2 | Existing canonical VerifiedPrincipal; effective OWNER/APPROVER, active membership/live credential; independent of affected material authors/contributors | Wrong actor/role, expiry/revocation, authorship, project rejection |
| §3 | Exact FROZEN/current-valid ScientificConclusionVersion; immutable complete typed input closure | Missing/stale/draft/cross-project/hash corruption |
| §3 | All eligible committed exact-target reviews, including REJECT/UNCERTAIN; at least one; matching corruption fails closed | Complete saved basis, deterministic ordinals, restart readback |
| §4 | Blocker iff same-project exact-target valid review Issue OPEN AND BLOCKING | Blocking/nonblocking/unrelated cases |
| §5 | Both writers acquire exact conclusion-version row FOR UPDATE; zero-Issue review INSERT participates; forbidden review/Issue UPDATE/DELETE stay forbidden | Direct SQL lock witnesses, both commit orders; no lifecycle expansion |
| §5 | request coordination → exact target → compatible parent/closure/authority → sorted review rows → Issue/basis; fresh post-wait statements and clock_timestamp authorization | Observed backend PIDs/blocking PIDs/deadlines; no sleep-only ordering |
| §6 | canonical DecisionRecord.id=request UUID; compare normalized existing caller material + authenticated actor/project/command, never server-selected basis as caller payload | Same/conflicting UUID; concurrent duplicates; unknown UUID |
| §6 | Existing immutable DecisionReadback: id/project/type/value/question/rationale/decided_by/decided_at, target hash, typed saved basis and basis/content hashes | Exact replay after STALE/original write-role loss only with current independent read authority; nondisclosing denial |
| §4 | At most one initial decision per project/exact-target/purpose across actors and UUIDs; existing typed relations enforce database scope guard | New UUID replacement/concurrent/direct SQL rejection |
| §3,6 | Literal R2 basis/content payload; no receipt/new digest/semantic column; immutable attributable decision fact; any existing creation audit mechanism is conditional, with no new audit schema | Golden R2 shape/hash tests; rollback/no duplicate audit |
| §6 | Existing ErrorCode categories; sanitize database errors and forbidden history | No protected identity or raw exception leak |
| §7 | Forward-only accepted migration changes: 0041 review coordination; 0042 minimal DecisionRecord and typed conclusion/review basis only; preserve every required physical FK/index/immutability rule | Single head; catalog inventory; data-preserving upgrade/downgrade |
| §1,7 | No Approval/grant/release/Issue disposition/RevisionAction/VERIFIED/manuscript or formal gate changes | Database side-effect assertions |

Existing canonical field/hash rules are inherited, never expanded. Anything not derivable is UNSPECIFIED and a STOP, not a subagent decision. The frozen contract explicitly allows implementation obligations without claiming they are already verified.

## Ownership and stage plan

- Integrator: this matrix, authoritative document import, UoW/port wiring if needed, integration, run logs/evidence/checkpoints, final verification and two independent reviews.
- Agent A isolated worktree: migration 0041, narrowly required internal-review repository lock order, `test_pr2_15_coordination.py`; no Decision command or 0042.
- Agent B isolated worktree: Application `decision.py`, persistence `decision_repository.py`, domain decision hash/readback helpers if necessary, migration 0042, focused unit tests. Does not edit UoW/ports or A/C files. Develop 0042 down_revision against agreed 0041 identifier `0041_pr2_15_review_coordination`.
- Agent C isolated worktree: `test_pr2_15_decision.py` and separate test helpers only; independently contract-derived adversarial PostgreSQL tests. No production/migration changes.

- [x] A writes red SQL coordination tests, witnesses old behavior, implements forward guards, verifies upgrade/downgrade and original PR2-14.
- [x] B writes red hash/command tests, implements frozen command and typed persistence, records any unresolved authority/closure writer issue immediately.
- [x] C writes independent tests against agreed command interface; fixtures stay TEST ONLY.
- [x] Integrator freezes/reviews Gate A before integrating B/C; separate evidence commit.
- [x] Integrator runs integrated disposable PostgreSQL, PR2-10–14 regression, Ruff/focused Pyright and architecture checks; freezes/reviews Gate B; separate evidence commit.

All test databases must be newly created, individually fixture-owned on port 55442. Read-only preflight verified `onephone|postgres|55442|/private/tmp/rb-m3-postgres|7695073913076924777`. Existing accepted conclusion fixture verifies identity before CREATE and uses UUID-named databases with cleanup. Agents use independent fixture-created databases, never retained state. Any production dependency/writer inconsistency or normative gap blocks affected gate. Two narrow remediation rounds maximum per gate. No remote push/protected merge/deployment.
