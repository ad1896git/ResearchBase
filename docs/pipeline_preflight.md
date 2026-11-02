# Kernel-isolated pipeline deployment rehearsal

This is an explicit maintenance command, not a scheduler, deployment, merge or authorization
entrypoint. It never calls a real launchd transport. HIGH-risk source review, seven existing CI
checks and owner approval/merge are required before any real online rehearsal. An isolated
rehearsal PASS is not a real scheduled-start, concurrency, merge or deployment PASS.

## Fixed command and writable capability

Use the absolute **project-owned** Python3.12 virtual environment, with caches disabled:

```sh
/ABS/REVIEWED_RUNTIME/.venv/bin/python3 -B -m scripts.pipeline_preflight run --root /ABS/PRIVATE_ROOT
```

The single writable root must be canonical, owned by the caller and mode0700. It must not
intersect any readonly online input (including either ancestor direction). It contains
`manifest.json`, SHA-pinned payload/config/plist inputs and generated `payload/attempt-N`
and `evidence/attempt-N`. No external output path is accepted. Preplaced symlinks/hardlinks
anywhere in the writable root are refused. Previously completed attempts cannot be silently
reused. Failed attempts are retained; an explicit correction must identify the exact prior
result digest:

```sh
/ABS/REVIEWED_RUNTIME/.venv/bin/python3 -B -m scripts.pipeline_preflight run \
  --root /ABS/PRIVATE_ROOT --correction-of PRIOR_RESULT_SHA256
```

There are at most three corrections after the initial attempt. A partial/unknown prior
attempt, a passed attempt, or any `possible_online_write` outcome refuses correction. No
automatic recovery, retry, log restoration or quota reset occurs. Root-local operator edits
for an authorized correction must update the explicit manifest and paths to `attempt-N`.
Original inputs, stdout/stderr and result inventories remain in earlier evidence directories.
A newly authorized operation uses a new root; this tool does not grant that authorization.

## Mechanism and host limits

A minimal bootstrap validates the plan without running payload, then starts the complete
orchestrator through macOS `/usr/bin/sandbox-exec`. Its kernel policy denies writes except
beneath the single root, denies network and all Mach lookup. All descendants inherit that
same policy, including native shell/dd/ln and a mistakenly unmocked service command. There is
no broker or weaker fallback, and no dependence on Python monkeypatching for write isolation.
The launchd/clock adapter is mocked *inside* the confined process for rehearsal semantics.

The bootstrap closes inherited descriptors, uses read-only `/dev/null` stdin and fresh output
pipes. It refuses inherited regular stdout/stderr before printing anything, since already-open
writable descriptors can bypass acquisition-time policy checks. Child environment is rebuilt;
HOME/TMP/cache paths are root-derived, user site disabled, `-B`/PYTHONDONTWRITEBYTECODE set.
Before scenarios, a protected root-local canary verifies actual native write denial and another
root-local file verifies permitted writes. No capability probe tries to write real online data.
The internal orchestrator entry also checks the active kernel policy; invoking it directly
without confinement refuses. `sandbox-exec` and sandbox-check APIs are host-specific/deprecated
or private facilities; absence or changed behavior is blocked, never treated as an OS PASS.

The kernel protects **outside-root writes by this process tree**, not malicious changes by
other unconfined host processes. Such online changes, including a legitimate timer tick,
make this rehearsal fail. Reviewed payload is SHA-bound; parent evidence/inputs are checked
against RAM inventories after execution and created with O_EXCL. This is not a claim of a
separate adversarial security domain for parent artifacts inside the same writable root.
No signal can weaken the kernel policy; unknown process termination or timeout is non-PASS.

## Closed manifest version1

All listed fields are required; unknown versions/fields are refused:

```json
{
  "version": 1,
  "python": "/ABS/REVIEWED_RUNTIME/.venv/bin/python3",
  "online_inputs": ["/ABS/ONLINE/control", "/ABS/ONLINE/runtime", "/ABS/ONLINE/service-inputs"],
  "script": "/ABS/PRIVATE_ROOT/deploy.py",
  "script_sha256": "64-lowercase-hex",
  "bindings": ["/ABS/PRIVATE_ROOT/fixture-bindings.json"],
  "plists": [
    {"role": "old", "path": "/ABS/PRIVATE_ROOT/mapped-old.plist", "sha256": "64-hex",
     "original_path": "/ABS/PRIVATE_ROOT/original-old.plist", "original_sha256": "64-hex",
     "path_mapping": {"/ABS/ONLINE/old/config.json": "/ABS/PRIVATE_ROOT/payload/attempt-0/fixture/old/config.json"}},
    {"role": "replacement", "path": "/ABS/PRIVATE_ROOT/mapped-new.plist", "sha256": "64-hex",
     "original_path": "/ABS/PRIVATE_ROOT/original-new.plist", "original_sha256": "64-hex", "path_mapping": {}}
  ],
  "timeout": 120,
  "deployment": {
    "version": 1,
    "head": "EXACT_REVIEWED_TOOL_AND_FEATURE_HEAD_40HEX",
    "required_feature54": "7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2",
    "runtime": "/ABS/REVIEWED_RUNTIME",
    "prior_runtime": "/ABS/READONLY_PRIOR_RUNTIME",
    "stamp": "uniquealphanumericstamp",
    "mappings": [{"source": "/ABS/ONLINE/control", "destination": ".pipeline/control"}],
    "path_aliases": {"/ABS/ONLINE/codex-home": "codex-home"},
    "rewrite_json": [".pipeline/control/CURRENT_TIMER_DEPLOYMENT.json", ".pipeline/control/CURRENT_AUTHORIZED_QUEUE.json", ".pipeline/control/old/config.json", ".pipeline/control/old/queue.json"],
    "prior_plist": "LaunchAgents/com.researchbase.pipeline-wakeup.plist",
    "executable_dirs": ["/usr/bin", "/bin"],
    "codex_version": "codex-cli 0.164.0"
  }
}
```

This shows field roles, not a ready deployment plan. Add nonoverlapping explicit mappings for
all required legacy files/plists, old queue controls, auth data and empty directories. Sources
must be included in readonly online inputs; destinations are relative to the derived fixture.
Read-only runtime/interpreter/PATH references are typed separately from mutable config/log/
CODEX_HOME/TMP paths. Old/new plist fields include actual StartInterval, RunAtLoad, complete
argv, WorkingDirectory and environment. Every writable path must resolve beneath the current
attempt; original and mapped bytes/hashes and exact mapping are retained. An unmapped LIVE
old config or stdout/stderr is refused **before the first scenario write**, not interpreted as
a new service because its argv differs from fixture-oldcfg. Unknown service identities or
subprocess commands never fall through to a real transport.

The standard deployment adapter automatically materializes the mappings and checks them,
executes the exact supplied payload bytes in normal and injected pre-install rollback phases,
simulates launchd/clock and verifies prior plist/pointers byte restoration. It supplies the
closed fixture manifest/snapshot interfaces used by the reviewed deployment payload, rather
than importing a previous ad hoc preflight. Payload must preserve that reviewed interface;
unknown new expectations fail rather than gain a permissive mock. The full historical payload
regression in the tests exercises normal installation and rollback with real-schema plists.
Runtime HEAD is exact and required-feature54 must be its verified ancestor; current main is
not hardcoded to remain754 after this tool merges. Actual live installer's source review and
matching baseline guards remain separate release obligations.

`deployment: null` is the generic isolation test harness: the same SHA-bound script receives
`--phase normal` (exit0) and `--phase rollback` (exit23). That mode is labeled generic and is
not accepted as the fixed deployment-adapter proof. No temporary Python wrapper is needed for
the deployment mode; only the reviewed payload and closed data manifest are provided.

## Whole-online comparison and results

Before and after execution, the confined orchestrator snapshots **every** file/directory
entry under all declared online inputs: full path membership, metadata and SHA256, including
logs, locks, empty directories and unreferenced history. Symlinks are recorded with lstat and
readlink target text/hash, without following them; readonly hardlinks include nlink/content.
No excludes or lock/PID writes occur online. Special input types or unstable scans block,
and inventory limits refuse rather than truncate. List complete control (including its logs),
active runtime, and explicit service/legacy inputs in an actual release plan.

Every difference, unreadable input, new/deleted entry or uncertain scan yields blocked,
`possible_online_write: true` and nonzero status; genuine natural-timer changes are not
filtered or retrospectively turned into unchanged. This conservative flag means possible
online change, not attribution to the payload. Correct result has `status: pass`, complete
identical before/after inventory, successful kernel probes, both reviewed phases, explicit
SIMULATED_ONLY transport and deployment NOT_EXECUTED. Caller must check adapter=deployment
for deployment readiness. Root reports can contain private engineering input bytes and must
remain private; only sanitized fixture evidence belongs in a PR.

Linux CI cannot provide Seatbelt: native Mac tests are explicitly platform-skipped and
unsupported runtime refuses. Actual LOCAL-MAC-PASS is separate evidence. Existing seven job
names, benchmarks, risk/approval policies, scheduler, scientific contracts and schema are
unchanged. No real online command may run until exact-source review, all seven CI and merge.
