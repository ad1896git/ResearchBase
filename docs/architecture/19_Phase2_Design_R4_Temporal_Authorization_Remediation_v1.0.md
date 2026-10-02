# Phase 2 Design R4 — temporal authorization remediation v1.0

**Status:** proposed normative design correction for independent review; design only. **Authority:** Addendum A20. **Scope:** the R3 review's remaining cross-expiry P1 finding. No Phase 1 semantic change, production code, migration, PR2-00, PR2-01 or Phase 2 implementation is authorized.

## 1. TEMP-AUTH-01 — final expiry-sensitive decision

For any authorization predicate whose truth can become false solely because wall-clock time advances, the final authorization decision **MUST** use a fresh trusted database time obtained **after every blocking lock required for the protected effect has been acquired and immediately before that effect**. The transaction-start timestamp is a historical transaction coordinate, not the fresh authorization time. In PostgreSQL, `CURRENT_TIMESTAMP`, `now()` and `transaction_timestamp()` are fixed at transaction start and **MUST NOT** serve as the final expiry-sensitive authorization time. The implementation uses an advancing trusted database-time primitive, `clock_timestamp()`, fetched after the locks and durable-state reread. A caller clock, previously sampled DB timestamp or cached authentication result cannot substitute for it.

The conceptual sequence for a first-time protected operation is:

```text
BEGIN
→ normalize request
→ acquire all blocking locks required for the protected effect
→ reread locked durable state
→ obtain fresh trusted authorization time with PostgreSQL clock_timestamp()
→ evaluate all expiry-sensitive authorization predicates at that time
→ execute protected effect
→ write durable result/receipt
→ COMMIT
```

Earlier checks may reject a request, but they cannot be the sole basis for an expiry-sensitive grant. If execution subsequently waits on another lock required for the effect, it MUST reread affected state and obtain another `clock_timestamp()` after that wait, then repeat the final authorization check before the effect. A serialization retry is a new attempt and repeats the full sequence. The final check uses half-open validity bounds: `not_before <= t < not_after`, `issued_at <= t < expires_at`, and `t < valid_until`, as applicable. Equality with an expiry instant denies. A transaction that started before expiry gains no right to act after expiry.

This rule applies to challenge consumption, effective project roles and credentials, grant validity, approver authority, scheduled membership/role expiry, current consent or other time-bounded Phase 2 authorization inputs. It changes the decision time, not historical event timestamps, immutable scientific facts, canonical hashes or one-command/one-transaction semantics. Where R2/R3 says “DB transaction time” for a final expiry-sensitive check, read it as this fresh post-lock authorization time. Historical `created_at`, `issued_at`, `ownership_started_at` and other recorded event times retain their own specified meanings.

## 2. Legacy actor enrollment challenge

The `bind_legacy_actor_subject` first-time path takes the deployment and challenge locks and any other locks needed for the binding, then rereads the challenge and relevant actor/subject state. It requires `status=ISSUED`, the exact challenge/attestation/principal tuple, trusted live response and subject eligibility. **After** acquiring those locks, it obtains `t=clock_timestamp()` from PostgreSQL and requires `issued_at <= t < expires_at`, plus the live credential and operator authority valid at `t`. It then marks that challenge CONSUMED and creates exactly one binding and binding event in the same SERIALIZABLE transaction, recording the result binding ID. Preallocated IDs and deferred FK checks may satisfy the cyclic commit constraints; no partial consumption or binding may commit. A wait for a further required lock forces a fresh reread/time/check before this state change.

Challenge-row locking and permanent challenge/nonce uniqueness serialize concurrent attempts. At most one enrollment may consume C. Once C is CONSUMED, revoking its resulting binding never changes C back to ISSUED and never allows reuse. A transaction beginning before `expires_at` but obtaining its required lock at or after `expires_at` fails `ENROLLMENT_CHALLENGE_EXPIRED` without creating a binding. A sweeper is not needed for expiry to take effect. The R3 challenge schema and proof requirements remain intact.

## 3. Effective OWNER and other role authorization

For a protected governance action, after its project, role/membership and target locks required for the effect, reread the locked durable state and obtain fresh DB authorization time `t`. At that time:

```text
effective_owner(actor, project, t)
  = role_binding_valid(actor, project, t)
    AND credential_valid(actor, t)
```

`role_binding_valid` means the actor is not retired, membership is ACTIVE at `t`, and an OWNER assignment covers `t` under its half-open interval. `credential_valid` retains R3's requirement for an active binding backed by the **actual** trusted verifier's credential validity and revocation state at `t`; a binding row alone is insufficient. The command also requires a live verified principal for that actor at `t`. If a trusted adapter cannot establish current credential validity at the post-lock time, authorization fails closed. Other time-bounded roles use the same final-time rule.

An open-ended OWNER assignment with sole credential expiry T authorizes at T−1 if every other predicate holds and denies at T and T+1, even with no database mutation. A transaction starting at T−1 and waiting for a required lock until T+1 must deny. The availability query evaluates an advancing trusted time when read; it does not treat an open role as proof of a valid credential. Credential expiry never rewrites historical role or membership intervals. R3's structural coverage and audited recovery ceremony remain unchanged; recovery's operator, challenge and new credential checks also obey TEMP-AUTH-01.

## 4. Governance grant first use and completed receipt replay

For a **first-time** `RECORD_INTERNAL_SCIENTIFIC_RELEASE`, `TRANSITION_PUBLICATION_READY` or `FREEZE_PREPARED_SUBMISSION` effect, obtain the command-key/grant/target/package and other required blocking locks, reread their durable state, then fetch fresh DB time `t=clock_timestamp()`. At `t`, recheck grant `ACTIVE` and `t < valid_until`, caller's effective role and live credential, issuing approver's effective HUMAN APPROVER authority, scheduled membership/role bounds, target validity, review/decision closure, blocking issues, current consent when required and all other R2/R3 gate predicates. Only then perform the protected transition or freeze and insert the consumption/result/event/receipt atomically. A wait for any further required lock repeats the final time-sensitive checks before mutation. Neither grant expiry nor authority expiry may be bypassed by a transaction-start timestamp or a pre-lock check.

An exact **completed receipt replay** is a read of historical committed effect, not another grant consumption or protected mutation. Authenticate the caller and locate the immutable receipt by globally unique command key. Require the authenticated actor and project to match the receipt before disclosing its result. For that actor/project, a changed canonical request hash or normalized command scope returns `IDEMPOTENCY_CONFLICT`; the key cannot be reassigned to a different grant or command. If the same key has the same R3 canonical request hash and scope and a durable completed prior result, return the saved result IDs/DTO; do not rerun the effect and do not require the expired grant or original effect authorization to become valid again. If the caller cannot authenticate or does not match the receipt actor/project, do not disclose the result. An absent or incomplete receipt cannot be treated as a completed replay: it enters the normal first-time path with fresh post-lock authorization or fails closed under the R3 atomicity rules. A different key is a fresh command and cannot reuse a consumed grant. This paragraph supersedes only R3's “checks current authentication/authorization even for replay” wording for a completed matching receipt; R3's request payload, hash, uniqueness and result semantics remain unchanged.

## 5. Required cross-expiry concurrency evidence for later authorized PRs

The future PR2-00 and governance evidence packs MUST specify and execute controlled concurrency tests on PostgreSQL 18.x. Use a barrier/held required lock so the protected transaction starts at T−1, blocks, acquires the lock at T+1, and reaches its final authorization check only then. Capture both the transaction-start timestamp and the post-lock `clock_timestamp()` to prove which instant decided the result. Do not accept a test that merely sleeps before starting a transaction.

| Case | Required lock and boundary | Required result |
|---|---|---|
| Legacy enrollment | Hold C's required challenge lock; C expires at T while the enrollment transaction waits. | DENY `ENROLLMENT_CHALLENGE_EXPIRED`; no binding/event/consumption commits. |
| OWNER governance action | Hold a required project/role/target lock; the sole OWNER credential expires at T while the transaction waits. | DENY OWNER authority; no protected effect or receipt commits. The open role remains historical. |
| Grant first use | Hold a required grant/target/package lock; grant `valid_until` or a required approver/caller role/credential expires at T while consumption waits. | DENY (`GRANT_INVALID`, `GRANT_STALE` or the applicable authorization error); no transition, freeze, consumption or receipt commits. |

Also test concurrent C consumption (at most one success), revoked-binding C replay (deny), exact completed grant receipt replay after original grant expiry (saved result, no new effect), changed-key/hash conflict, and serialization retry after T (fresh check denies). These cases are specifications for later authorized work, not tests executed by R4.

## 6. Scope and stop

All 21 R2/R3 golden hash vectors and their canonicalization rules remain byte-for-byte unchanged. P1-03 basis ordering, P1-12 identifier correction provenance, grant replay request identity, LiteratureEvidence and ManuscriptVersion vectors, initial identifier primary semantics, publication/governance purpose tuples and Phase 1 v4 semantics retain R3 precedence. R4 admits no schema and authorizes no implementation. Independent review of the committed R4 design is required before the design may be presented for human Phase 2 reauthorization. `READY_FOR_PHASE2_REAUTHORIZATION=NO`, `PHASE_2_AUTHORIZED=NO`, `READY_FOR_PHASE2_IMPLEMENTATION=NO`, `NEXT_PR=NONE` until that review.
