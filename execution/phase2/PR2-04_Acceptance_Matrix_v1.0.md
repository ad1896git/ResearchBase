# PR2-04 acceptance matrix v1.0

**Status:** design-review candidate; all requirements NOT_RUN. This is a specification, not generated evidence. Applies only after [pack](PR2-04_Literature_Search_Execution_Execution_Pack_v1.0.md) and [ADR-0011](../../docs/architecture/adr/ADR-0011-search-execution-attempt-accounting.md) approval. Source aliases S01–S16/C01 are defined in pack §2. No requirement retroactively strengthens accepted PRs.

There are **65 required requirements** below. Each ID is stable. Each row may bind several tests/parameters; **all** must be accounted for. Future machine result follows pack §22 and contains exact collected node IDs, candidate SHA and trace artifacts. Not-run, skipped, xfailed, missing or stale-head evidence cannot be PASS. Runtime Required equals the number of rows, not a fixed imitation of PR2-03. Design-time counts: Required=65, PASS=0, FAIL=0, BLOCKED=0, NOT_RUN=65. These are specification states, not an attempted host run.

Evidence types: `U` deterministic unit/golden-vector output; `PG` real PostgreSQL18 integration/direct-SQL evidence; `TRACE` machine-readable causal/attempt trace and durable row counts; `API` HTTP/CLI parity; `MIG` migration graph/upgrade/downgrade output; `REG` accepted regression output; `STATIC` static/scope audit. Fake providers only; no external service is needed.

## Domain and request contract

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-DOM-01 | Complete execution transition matrix, including every forbidden terminal exit and PLANNED→invalid terminal; pack §6, S03/S08. | U + PG | unit lifecycle; application |
| PR204-DOM-02 | RESERVED attempt seals once to a valid complete outcome; uncertainty cannot be relabeled safe; pack §§6,10,13.5. | U + PG | unit state machine; persistence |
| PR204-DOM-03 | Closed DTOs, limits, normalized query text, pinned provider/plan compatibility; exact frozen plan and verified hash, no current-pointer substitution; pack §§5,8,11. | U + PG | validation; application |
| PR204-DOM-04 | FROZEN at creation/first start; supersession after start retains exact historical material; invalid/unfrozen/cross-project plan rejects; pack §§5,12. | PG + TRACE | lifecycle/closure integration |

## Persistence

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-DB-01 | Every §13 column/nullability/CHECK/unique/same-parent FK and RESTRICT behavior enforced with direct SQL invalid cases; S08/ADR-0011. | PG | schema guards |
| PR204-DB-02 | Every FK has leading B-tree coverage; required query/status/scope indexes exist; pack §13. | PG | FK-index inspection |
| PR204-DB-03 | Execution material/terminal rows immutable; CAS and row_version exact increments; stale write cannot overwrite; pack §§6,13. | PG + TRACE | persistence/concurrency |
| PR204-DB-04 | Query/result append-only; atomic seal prevents late append or orphan query/result; direct SQL cannot bypass execution lock/terminal guard; pack §13. | PG | direct SQL guards |
| PR204-DB-05 | Attempt reservation fixed, one unsealed per execution, bounded contiguous attempt numbers and valid input index; outcome write once; terminal execution cannot gain attempts; pack §§13.1,13.5. | PG | persistence constraints |
| PR204-DB-06 | Events contiguous/append-only, one cancel intent/finish, state/version equality; no lifecycle event after terminalization. Immutable scoped receipts permit only explicitly authorized new terminal RECOVER no-op admissions, with no state/version/provenance/event change or provider call; exact replay inserts nothing; pack §§11,13.1,13.6–13.7. | PG + TRACE | audit/receipt atomicity and terminal exception |

## External boundary and success

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-BOUND-01 | No open service transaction/connection-held locks during provider entry, wait or backoff; S05 §30, TDG2-06, pack §7. | PG + TRACE | boundary observer |
| PR204-BOUND-02 | TX A commit precedes invocation; TX B atomic outcome precedes TX C terminal; no provider call in DB retry closure; pack §7. | TRACE + PG | causal transaction trace |
| PR204-BOUND-03 | Only definitely acknowledged new reservation gets one local invocation; existing reservation/lost commit ack never dispatches; pack §§7,19. | TRACE + PG | external ownership fault injection |
| PR204-SUCCESS-01 | One-query success and zero-hit success have correct states, times, receipts and complete provenance; pack §§5–7. | TRACE + PG | application success |
| PR204-SUCCESS-02 | Multiple input queries run sequentially; success requires each; partial prior hits retained on later failure; no source/evidence created; pack §§6,15. | TRACE + PG | multi-query success/failure |

## Provider retry and failure

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-PROV-01 | Known 429/transient 5xx/NOT_SENT transport failure retries only after outcome commit, distinct counted reservation/query; TDG2-07, pack §9. | TRACE + PG | fake-provider retry |
| PR204-PROV-02 | Retry-After honored, exponential jitter bounded, cap/config/time budget enforced, no adapter-hidden retries; pack §9. | U + TRACE | retry policy/fake clock |
| PR204-PROV-03 | Permanent/auth/validation provider failure never retries; exhaustion preserves prior reasons and ends FAILED; pack §§9,16. | TRACE + PG | provider failures |
| PR204-PROV-04 | Malformed, oversized, echo-mismatched/nonfinite provider response rejects atomically; no partial result salvage/raw error leak; pack §§8,16. | U + PG + TRACE | adapter contract validation |

## Timeout, uncertainty and cancellation

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-UNKNOWN-01 | Timeout proven NOT_SENT is safely retryable with bounded exhaustion, not fabricated success; pack §§9–10. | TRACE + PG | timeout fake |
| PR204-UNKNOWN-02 | Timeout/disconnect after possible dispatch persists UNKNOWN and suppresses all subsequent provider attempts/queries; TDG2-06, pack §10. | TRACE + PG | uncertain-delivery fake |
| PR204-UNKNOWN-03 | Expired unresolved reservation recovery is conservative UNKNOWN with no fabricated invoked_at/query/result; before deadline recovery denies; pack §§10,19. | TRACE + PG | recovery deadline |
| PR204-UNKNOWN-04 | UNKNOWN is terminal; exact replay/late provider response never reopens or redispatches; explicit new execution remains distinct; pack §§9–11. | TRACE + PG | uncertainty replay/fencing |
| PR204-CANCEL-01 | Cancel PLANNED normally: C1 commits unique CANCEL_REQUESTED and admission receipt with one version bump; separate C2 commits CANCELLED/FINISHED with one further bump, null started_at and zero provider calls. Admission never claims finalization; pack §§6–7,10,13.6. | TRACE + PG | pre-dispatch cancellation coordinates |
| PR204-CANCEL-02 | Cancel during provider interaction: confirmed cancellation vs uncertain cancellation remain distinct CANCELLED/UNKNOWN; pack §10. | TRACE + PG | cancellation fake/barrier |
| PR204-CANCEL-03 | Cancel between attempts prevents next reservation and retains prior hits; completed response may be preserved without claiming execution success; pack §10. | TRACE + PG | cancellation after response |
| PR204-CANCEL-04 | HTTP disconnect/cooperative token alone is not forged durable cancellation; terminal-wins cancellation denies without rewrite; pack §§10,17. | API + PG | cancellation transport |

## Idempotency and command results

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-IDEM-01 | All four commands same complete receipt key + same normalized payload returns identical admission after current entitlement; no repeated effects/provider call. Cancel contenders before C1 commit admit once (rollback admits nothing); replay after C1/before C2 and after CANCELLED returns the same admission without finalizing; pack §11. | PG + TRACE + API | parameterized command replay and cancellation timing |
| PR204-IDEM-02 | All commands same complete key (deployment_id,actor_id,project_id,command_name,request_id) + materially different payload/hash yields IDEMPOTENCY_CONFLICT; conflict/pre-admission rollback leaves no new receipt/effect. Scope change is not this case; pack §11. | PG + TRACE | same-key payload conflict/rollback |
| PR204-IDEM-03 | Same request UUID under different valid receipt scopes is independent, subject to normal command checks. Separately UNIQUE(project_id,idempotency_key) prevents duplicate create across actor/deployment scopes in the same project with non-disclosing conflict; different valid projects remain independent; pack §11. | PG + TRACE | distinct-scope receipts versus execution uniqueness |
| PR204-IDEM-04 | PLANNED/RUNNING/FAILED/CANCELLED/UNKNOWN/SUCCEEDED exact replay is read-only; admission is not final-success/cancellation. New terminal cancel/execute denies with no receipt; new authorized terminal recover can persist only a no-op receipt, never new work or altered facts; pack §§11,13.1,17. | PG + TRACE + API | operational replay states and receipt exception |
| PR204-IDEM-05 | Explicit new execute key can drive only known-safe remaining work; unresolved/terminal/stop conditions cannot be bypassed; pack §§9,19. | PG + TRACE | restart/continuation |
| PR204-IDEM-06 | Post-admission error preserves legitimate earlier receipt; lost response/replay recovers admission without claiming whole-operation rollback; pack §§11,19. | PG + TRACE + API | multi-phase receipts |

## Provenance and hashing

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-TRACE-01 | Typed plan→execution→attempt→query→result chain and uncertainty gaps reconstructable; same-project consistency; pack §§13,15. | PG + TRACE | provenance query |
| PR204-TRACE-02 | Contract15 query golden hash literal/normalization unchanged; identical retried text has separate ordinal/hash; pack §13.3. | U + PG | golden vectors/ordering |
| PR204-TRACE-03 | New result golden hash literal/decimal/null rules; provenance reads verify stored query/result digests and fail closed on corruption; pack §13.4, ADR-0011. | U + PG | golden vectors/corruption |
| PR204-TRACE-04 | Stable contiguous query/rank/event order; duplicate provider IDs remain separate hits; no source resolution/dedup/evidence mutation; pack §§5,15. | PG + TRACE | ordinal/duplicate integration |

## PostgreSQL concurrency

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-CONC-01 | Duplicate create both winner orderings: actual PostgreSQL wait, one execution, exact replay/conflict, canonical uniqueness normalization; pack §18. | PG + TRACE | five parameterized races/order |
| PR204-CONC-02 | Competing execute drivers/restart: one reservation owner/invocation, no takeover; blocker/PIDs and call counts retained; pack §§7,18. | PG + TRACE | five races/order |
| PR204-CONC-03 | Outcome vs expired recovery both orderings: complete success or UNKNOWN fence, never mixed/late append. Recovery vs recovery, both orderings, for expired RESERVED and C1-committed PLANNED cancellation: one seal where applicable, one terminal transition/FINISHED, loser retries/rereads durable state, separately scoped no-op receipts only; zero recovery provider calls or duplicate query/results; pack §§10,18–19. | PG + TRACE | five races/scenario/order; state/CAS fencing |
| PR204-CONC-04 | Cancellation vs reservation and TX C both orderings: deterministic permitted state, one terminal event; pack §§10,18. | PG + TRACE | five races/order |
| PR204-CONC-05 | Inherited 40001 and PR2-04-specific 40P01 mapping yield CONCURRENT_MODIFICATION within bounded per-phase DB retry, fresh reads/authority and canonical exhaustion; cover admission, TX B and finalization, no repeated provider/partial current-phase writes. Verify wrapper scope and earlier services' existing 40P01 behavior unchanged; global policy expansion requires separate approval and historical non-drift proof; pack §9. | PG + TRACE + REG + STATIC | SQLSTATE retry/exhaustion and isolation regression |
| PR204-CONC-06 | Complete attempt accounting distinguishes DB/provider/command retries, reports all SQLSTATEs and durable outcomes without retries hidden by test rerun; pack §§9,22. | TRACE | evidence integrity |

## Authority and security

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-AUTH-01 | HUMAN/AGENT start/write/read role matrix, verified principal, cross-project non-disclosure, no bare actor-ID authority; pack §12, S10–S14. | PG + API | authority matrix |
| PR204-AUTH-02 | Required-lock contention then role/credential expiry uses fresh clock_timestamp on every retry; denies with zero forbidden new effects; pack §§12,18. | PG + TRACE | five temporal races/case |
| PR204-AUTH-03 | Loss during provider call denies original TX B/TX C/disclosure; earlier admission distinguished; no newly unauthorized query/result/receipt/event; pack §12. | PG + TRACE | external-call authority race |
| PR204-AUTH-04 | Current authorized recovery actor may close pending work, not impersonate initiator/accept unproved response; VIEWER cannot recover or replay writes; pack §§12,19. | PG + TRACE | recovery authorization |
| PR204-SEC-01 | Secret canaries absent from canonical rows/receipts/errors/logs/XML/JSON; no raw payload/credential DTO, implicit fetch or live egress; pack §§8,22. | U + PG + TRACE | redaction/security boundary |

## Crash boundaries

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-CRASH-01 | Before TX A commit/lost acknowledgment: zero or one execution determined by request key; no invocation from uncertain commit; pack §19. | PG + TRACE | fault injection |
| PR204-CRASH-02 | After create commit before reservation: PLANNED survives, replay read-only, explicit start/cancel safe; pack §19. | PG + TRACE | restart recovery |
| PR204-CRASH-03 | After reservation before call and during call: no takeover; bounded UNKNOWN recovery retains ambiguity; pack §19. | PG + TRACE | two fault positions |
| PR204-CRASH-04 | Provider return before TX B: lost response remains UNKNOWN; surviving owner persists without second call only after current auth; pack §19. | PG + TRACE | response-loss fault |
| PR204-CRASH-05 | TX B rollback/lost commit response: whole response or none, exact sealed replay no duplicate rows/call; pack §19. | PG + TRACE | transaction commit fault |
| PR204-CRASH-06 | After TX B/before TX C or during backoff: facts retained, recovery derives outcome or stops known-incomplete, never invents remote outcome; pack §19. | PG + TRACE | inter-phase interruption |
| PR204-CRASH-07 | During TX C/C2: one terminal/event, fresh CAS/authorization, no provider. Crash after C1 intent/receipt commit before C2: PLANNED + intent survives, replay admission does not finalize; new authorized recovery converges CANCELLED exactly once, no duplicate FINISHED/protected effects. PLANNED without intent stays PLANNED; concurrent recovery covered by PR204-CONC-03; pack §§10,18–19. | PG + TRACE | finalization fault and interrupted cancellation recovery |
| PR204-CRASH-08 | Final commit before caller response: replay admission and current terminal query agree on identity; no new invocation; pack §19. | PG + TRACE + API | lost client response |

## Transport, migration, regression and evidence

| Requirement ID | Invariant / source | Evidence | Expected category |
|---|---|---|---|
| PR204-API-01 | HTTP/CLI parity, request UUID/closed payload/error/response contracts, in-progress admission versus state; no public result-injection path; pack §17. | API | transport validation |
| PR204-API-02 | Project-scoped get/list/provenance stable cursor/limits, current read authority, typed DTOs not ORM; pack §§12,15,17. | API + PG | retrieval/pagination |
| PR204-MIG-01 | Fresh/0018/populated0023a upgrades, exact parent and unique0024 head, existing data intact; pack §14. | MIG + PG | migration upgrade |
| PR204-MIG-02 | Empty-only downgrade/reupgrade; each populated new table blocks downgrade before DDL; no historical migration rewrite; pack §14. | MIG + PG | migration safety |
| PR204-REG-01 | Phase1 frozen behavior, hashes, migrations unchanged; no PR2-05/06 production or framework/live-provider expansion; pack §§3–4,24. | REG + STATIC | architecture/non-drift |
| PR204-REG-02 | Accepted PR2-00 temporal, PR2-01 identity, GOV bridge, PR2-02 durable acceptance, PR2-03 abandon/authority/identity/DB guards and0023/0023a preserved; pack §22. | REG + PG | accepted regression ladder |
| PR204-REG-03 | Ruff/Pyright/diff check PASS; changed files formatted, zero new formatter failures vs accepted baseline; pack §22. | STATIC | static gates |
| PR204-EVID-01 | Exact candidate HEAD/PG version/migration/timestamps/invocations, per-case traces, complete requirement-level matrix; no stale/summary-only PASS; pack §22. | TRACE | host evidence validator |
| PR204-EVID-02 | Candidate-bound full suite exact collected/passed/failed/errors/skipped/warnings; zero failures/errors/required skips; pack §25. | REG | full suite |

## Review use

The matrix intentionally separates uncertainty, crash positions and retry domains: one generic success test cannot prove them. Parameter expansion is part of the implementation evidence binding, not an opportunity to reduce coverage. All rows remain required if test files are reorganized. Any waived or altered invariant requires design review, not a hand-edited PASS value.

Design-only delivery does not run this matrix and does not authorize implementation. Independent reviewers should attack the pack/ADR first; executor host evidence belongs to a later explicitly authorized implementation candidate.
