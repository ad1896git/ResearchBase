PROPOSED / NON-NORMATIVE / NO IMPLEMENTATION AUTHORITY

Source baseline: `7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2`. This is the P05 docs-only preparation child, not a scientific contract freeze, architecture change, executable packet, facility authorization or whole-P05 completion. Parent risk stays HIGH. OBSERVED_SOURCE means inspected static code; HISTORICAL_ACCEPTANCE means a cited acceptance record, not a new test. All proposed behavior below is PROPOSED. Environment, actual backend and independent review are UNVERIFIED/UNASSIGNED_OWNER_INPUT.

# Future acceptance allocation — design only, tests NOT RUN

This plan proposes future evidence after exact contract/source/facility authorization. No project commands, fixtures, candidate programs, gateway calls, DB, provider or compute actions are run by this docs-only child. Exact assertions/ErrorCodes/state labels follow the later approved contract. Source and historical facts are mapped in `evidence-map.md`.

| Group | Proposed meaningful case and required observation | Facility / owner gate |
| --- | --- | --- |
| Codec and refs | Literal positive/negative request/result bytes/digests, unknown/duplicate fields, bool/int/null/float/oversize, foreign project, missing/unreadable frozen version/hash, modified policy/adapter/Harness pin; deny with zero partial writes | Offline units only after codec freeze; true owning reference/permission cases real PG18 |
| Intent atomicity | Kill before/after intent/reservation/receipt commit, including lost commit response; original command reconciliation returns one original receipt or exact rollback, never new action/reservation | Real PG18 Application/UoW and fault-controlled process; isolated test database authorized separately |
| Claim competition | Two genuine workers claim same action; wait then expiry/revoke/policy drift; trusted DB time sampled after wait; only one permitted owner/epoch; immutable ownership history retained | Real PG18 barriers/transactions, approved lock inventory and backend-fence contract |
| External send windows | Kill around marker/send/backend accept/handle save. Resolve by original correlation key; missing handle stays UNKNOWN. Backend authoritative not-accepted may allow same-key retry only under frozen rule | P03/P06 approved isolated Linux/backend; fake is contract coverage only |
| Expiry/reclaim | Old worker send resumes after TTL; new claim cannot create second job. Demonstrate backend fence/idempotency actually rejects duplicate/stale epoch, not only local mutex | Real approved P06 backend; separate containment/facility evidence |
| Original receipt recovery | Repeated worker restart/recovery and duplicate/out-of-order delivery retain original action/request/receipt and at-most-one logical acceptance | PG18 plus approved backend; no engineering ledger as scientific owner |
| Current entitlement | Revoke writer/read access or change policy before claim/ingest/replay; current read entitlement controls disclosure while historical receipt bytes remain unchanged | PG18 owning authorization and lock-wait tests |
| Finish/commit unknown | Complete job but lose observation/ingest/settlement response; exact original receipt resolves outcome. No repeat send, refund or synthetic Run by absence | PG18 + backend receipt retention contract |
| Cancel/late outcomes | Cancel request timeout; confirmed cancel vs still-running; completion races cancellation; preserve late failure/success and original correlation | P06 backend and owning Application cancellation contract |
| Accounting | Unknown retains reservation; duplicate/replayed finish has no second spend; frozen units/caps exhausted hard-stop; lease expiry never refunds or resets budget | PR3-04 owning PG18 reservation/usage invariants; backend metering reviewed |
| Negative science | Failed/negative/invalid results retained with provenance, never hidden by retry-until-success; Run creation/seal only by owning scientific commands | Future P12/owning producer and real PG18, not this dispatcher |
| Invalid/stale input | Wrong actor/task/step/action/digest, foreign handle/receipt, stale epoch/version, expired deadline/credentials/policy; no backend send or zero partial ingest | Unit + PG18 + approved P06 negative backend observation |
| Containment/injection | Payload requests host-home/socket/secrets/network or provider SDK; source/artifact/prompt text cannot grant authority; no hidden subtool/self-promotion | P03 actual Linux containment intake; engineering Mac sandbox result not substitute |
| Restart retention | Original full request/digest/key/receipt survive process loss; backend retention expired/unresolvable remains held requiring owner disposition | Durable carrier/storage exact design review first; real PG/backend restart |

## Fault schedule and evidence

Assign immutable case IDs after contract freeze to A-before/A-after through F-before/F-after in the draft timeline. For every case capture exact source HEAD, contract/adapter/policy hashes, input bytes, original action/command/receipt IDs, trusted DB timestamps and actual lock/blocker order, fault boundary, external observed key/handle, transaction disposition and authoritative reservation/usage. Preserve every original attempt; no reset of budget or identity. A test should show denied dispatch through a real observed backend counter/journal, not infer no effect from a missing local row.

Separate results: fake contract tests, real PG atomicity, actual backend idempotency, actual Linux containment, scientific producer attribution and source CI are different gates. No fake/import/matrix/history result is reported as real PG/backend/production acceptance. Full seven-check source CI and independent review on the exact eventual implementation head remain required; no new CI test names or benchmark deferral is proposed.

## Exit criteria and visible holds

Preparation acceptance is exactly these three new documents, correct baseline citations, explicit unresolved choices and independent read-only review; publication is a separate host action. This does not close P05 whole, P06/P12, unattended execution, scientific architecture, memory save or real provider gates. Source cannot begin until storage/bytes/lease/fence/unknown/receipt/accounting interfaces and exact allowlist are reviewed, owning implementation authorized, and relevant PG18/P03/P06 facilities explicitly supplied. If any prerequisite is missing, record HOLD rather than install, select a backend or manufacture a positive execution.
