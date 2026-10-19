# Director ruling — 2026-10-19

**RESOLVED by director ruling.** The owner directs full B02 first-slice implementation
for verified HUMAN writers/readers. Application policy remains actor-type neutral.
No Agent bypass, binding, Human-for-Agent substitution or identity-guard change is
authorized. The verified Agent positive fixture is replaced by fail-closed
unbound/AGENT denial with existing FORBIDDEN. Agent writers await an owning
identity/provisioning contract in Phase 3; policy code needs no change.
Contract §§12.4–12.5 record this boundary. The evidence below is historical and
retained, not a current stop instruction or evidence of B02 implementation.

---

# B02 first-slice implementation blocker — review remediation 2026-10-19

**Historical blocker (resolved below).** The original stop was based on
an unmet identity prerequisite, with the normative chain and a runnable PostgreSQL
reproduction below. The earlier removed-fixture setup error was insufficient
proof; its log has been replaced by an isolated reproduction with positive controls.

## Exact contract chain

B02 does not itself literally say “Agent actors must hold subject bindings.” It
requires verified Agent callers using the existing identity interfaces. That
binding requirement comes from the identity contract B02 explicitly carries in
§1. This is the complete chain, rather than a claim that B02 contains that sentence:

| Source and exact location | Exact text / implication |
| --- | --- |
| `docs/proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md:126`–127, §3.5 | “Active verified OWNER/RESEARCHER in the same active project may capture/admit; Human and Agent follow identical policy.” |
| Same file, `:522`–523, §12.3 step 3 | “Use existing ArtifactStore/repositories, verified principal and credential interfaces.” |
| Same file, `:542`, §12.4 | Required PG fixture includes “verified Human/Agent writers/readers and separate capture/admission actors”. This is positive Agent coverage, not merely denying an unbound Agent. |
| `docs/architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md:7` | “An authenticated principal is derived by a deployment adapter and bound to an actor through `actor_subject_bindings` (0019).” Also: “A missing/ambiguous/revoked binding fails closed.” |
| Same identity contract, `:29` | “Agents obey identical Application policy after authenticated binding.” This expressly applies the binding prerequisite to Agents. |
| Same identity contract, `:15` | Provisioning “creates a new HUMAN actor and binding atomically”; “Service/Agent provisioning is a separate reviewed adapter policy and cannot use human proof.” |
| `migrations/versions/0019_phase2_bootstrap_membership.py:295`–300 | `rb_phase2_guard_human_actor()` checks `actor_type = 'HUMAN'`; otherwise raises `subject binding requires a HUMAN actor`, SQLSTATE `23514`, constraint `ck_actor_subject_binding_human`. |
| Same migration, `:1063` | `CREATE TRIGGER trg_actor_binding_human BEFORE INSERT ON actor_subject_bindings ... EXECUTE FUNCTION rb_phase2_guard_human_actor()`. Line 1066 also attaches it to enrollment challenges. |

B02's required successful verified Agent fixture cannot be constructed using the
existing identity interface. Allowing Agent principal assertions without bindings,
changing the identity guard, or replacing Agent attribution with a Human would
change the governing policy rather than substitute a name/location equivalent.

## ADR and existing-equivalent investigation

`docs/architecture/adr/ADR-0020-candidate-promotion-admission.md:51`–59 was rechecked:
it expressly permits verified Human/Agent writers, but supplies no Agent credential,
provisioning ceremony, sponsor mapping, or exception to the binding prerequisite.
Lines 194–206 retain existing owners plus the approved typed relations: four B02
tables, one B03 table, and no silent change to frozen numbered architecture. Its
accepted status authorizes those relations, not an unspecified identity policy.

Read-only repository searches for `sponsor`, `agent_identity`, `agent_identities`,
`AgentIdentity`, `agent_subject`, and `agent_bind` in `src`, `migrations`, the ADRs
and B02 found no Agent identity table or sponsor authentication path. All later
migrations were checked for redefinition of `rb_phase2_guard_human_actor`; none
replaces it. The reproduction also inspects the live trigger and function after
upgrading to the actual head, so the argument does not rely only on migration 0019.

The existing alternatives were inspected concretely:

- `src/researchbase/persistence/phase2_identity_repository.py:18`–40:
  `resolve_bound_subject` joins `actor_subject_bindings` and explicitly requires
  `a.actor_type='HUMAN'` at line 28. `resolve_local_binding` does likewise at line 53.
- `src/researchbase/hg1_runtime.py:194`–197 uses that same resolver.
  `src/researchbase/hg1_identity.py:130`–145 requires its resolved actor ID to equal
  the credential actor ID. It cannot authenticate an Agent via a different Human.
- `src/researchbase/persistence/literature_search_plan_repository.py:61`–63 joins
  the binding to the principal's exact actor/deployment/subject/credential.
  Existing role-policy parity does not supply the missing Agent binding ceremony.

A Human operating an Agent tool can use the Human's identity, but the attributable
caller is then HUMAN. This does not satisfy the required verified AGENT writer
fixture. No approved Human-sponsor-to-Agent attribution equivalent was found.

## Independent PostgreSQL reproduction

Runnable file: [test_b02_identity_boundary.py](../../../tests/integration/phase2/test_b02_identity_boundary.py).
It uses a disposable migrated PostgreSQL 18 database, not the removed B02 fixture,
and performs identical raw binding INSERTs for HUMAN and AGENT across both existing
subject kinds. Each test inspects the enabled live guard definition. HUMAN is a
positive control; AGENT asserts the exact driver SQLSTATE, constraint and primary
message. Writes roll back; no production provisioning success or complete ceremony
is claimed from the HUMAN INSERT control.

Environment for the commands below:

```sh
export UV_CACHE_DIR="$PWD/tmp/uv-cache"
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
```

The cache override is necessary because this sandbox cannot write the default
`/Users/fengwang/.cache/uv`. DATABASE_URL is the configured local lane test database;
the fixture creates and drops a random disposable database.

```sh
uv run pytest tests/integration/phase2/test_b02_identity_boundary.py -q -s -o addopts='' > docs/verification/b02/agent-binding-blocker-pg.txt 2>&1
```

**4 passed, 4 warnings in 6.64s**, exit 0. Both AGENT cases were rejected by
`ck_actor_subject_binding_human`; both HUMAN controls accepted the INSERT.
[Exact retained output](agent-binding-blocker-pg.txt). This is passing evidence
of the current prerequisite failure, **not** B02 admission acceptance.

## Reported restart failure and clean HEAD comparison

The exact requested focused command was run on this tree:

```sh
uv run pytest tests/integration/phase2/test_pr2_04_restart_completion.py -q
```

Exit 0, both cases passed (double quiet suppresses the numeric summary). It was
then rerun with only the quiet default cleared to retain explicit counts:

```sh
uv run pytest tests/integration/phase2/test_pr2_04_restart_completion.py -q -o addopts='' > docs/verification/b02/restart-current.txt 2>&1
```

**2 passed, 2 warnings in 5.04s**, exit 0. [Output](restart-current.txt).

Clean HEAD `672f2501e37af8143a2322ffdb769eacbf6e835e` was extracted with `git archive
HEAD` into ignored `tmp/b02-clean-head` without creating a branch or worktree.
Every tracked `src/` and `tests/` blob in that copy was checked against HEAD; see
[verification manifest](clean-head-verification.json). From that clean directory:

```sh
uv run --no-sync pytest tests/integration/phase2/test_pr2_04_restart_completion.py -q -o addopts='' > <repository>/docs/verification/b02/restart-clean-head.txt 2>&1
```

The locked repository `.venv` was reused via symlink, and PYTHONPATH explicitly
pointed at the clean copy's `src`. **2 passed, 2 warnings in 4.08s**, exit 0.
[Output](restart-clean-head.txt). Thus the reported failure was not reproduced on
either tree. These runs do not prove its cause, a flake, or a pre-existing failure.
No production code or restart test was changed to conceal it.

## Required check chain and remaining boundary

The owner's newly requested full check superseded the earlier no-whole-suite
instruction and was attempted exactly, after the environment exports above:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Observed by this agent: pyright **0 errors, 0 warnings, 0 informations**; Ruff format
**737 files already formatted**; Ruff lint **All checks passed!**; diff check exit 0.
The sharded runner could not remove mutex directories it classified as stale under the external
`.pipeline/logs` writable-root boundary. It repeatedly reported `Operation not
permitted`; the waiting loop was interrupted (exit 130). **No full-suite shard
ran; the required chain is not PASS.** [Runner output](full-suite.txt).
No mutex/runner bypass or weakening of checks was attempted; no external file
was modified by the denied runner operations. The static observations above are this agent's own runs, not
borrowed from the prior harness run. The four static checks were rerun after
remediation, all exit 0; [retained output](static-checks.txt).

The focused unit/architecture run also completed:

```sh
uv run pytest tests/unit tests/architecture -o addopts='' -q -p no:cacheprovider > docs/verification/b02/unit-architecture.txt 2>&1
```

**5637 passed, 49 warnings in 114.09s**, exit 0.
[Exact output](unit-architecture.txt). A final `git diff --check HEAD` also returned
exit 0 after the evidence update.

Implementation remains stopped under the owner's architecture-contradiction rule.
The requested approval status is preserved with an adjacent blocker pointer.
No B02 migration or production implementation remains, and no B02 gate success is
claimed. Resolution requires either an approved Agent authentication/provisioning
contract with explicit identity-change scope, or a B02/ADR amendment bounding this
first slice to Human admission and deferring Agent parity. An explicit contract
choice was requested while independent verification continued.

No commit, push or branch creation occurred.
