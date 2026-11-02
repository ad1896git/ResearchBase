# P04 / PR3-08 fake candidate preview slice

This is a deterministic, in-memory **candidate preview**, not the formal
`CodingCapability.execute_task` implementation in Phase3 architecture §§10–11.
It does not complete whole P04. Owner-directed scope was independently reviewed
and frozen as seven paths; scoped and parent risk remain medium, with independent
implementation review, exact-head seven required CI checks and owner merge gate.
No production composition registers this preview.

## Boundary and inputs

`FakeCodingCandidatePort.preview(FakeCodingCandidateRequest, CanonicalContext)` is
implemented by `FakeCodingPreviewAdapter`. All new public values are frozen,
slotted, keyword-only dataclasses, with exact types and immutable tuples. Unknown
constructor fields reject. Values are checked again at preview/result boundaries.
Existing sanitized `VALIDATION_ERROR` and scope-only `FORBIDDEN` are reused.
No provider, filesystem, process, database, ArtifactStore, clock, random generator,
callback, workspace discovery or other external I/O is used.

Request fields are project/task/optional step, an exact artifact SourceReference,
workspace fixture digest, objective, allowed paths/commands/tests, fixed policies
NO_INSTALL and DENY, declared seconds and fixture files. Commands are argv+cwd
**declarations**, never shell instructions to execute. Test commands must be a
unique subset of allowed commands. Declared time/dependency/network limits do not
certify a sandbox or enforce runtime permissions outside this pure preview.

| Input | Exact bound / behavior |
|---|---|
| UUID/hash | Exact non-nil UUID; lowercase 64hex SHA256 |
| Objective | Nonblank NFC UTF8, at most 8192 bytes; instruction text remains inert |
| Paths | 1–32 sorted unique POSIX file paths, at most 256 UTF8 bytes each; no dot/dotdot/empty components, absolute paths, backslash, control characters, wildcard/URL/query forms or surrounding whitespace; cwd additionally permits exact `.` |
| Commands/tests | At most 16 unique per tuple; 1–32 NFC, nonblank argv tokens per command, at most 256 bytes per token; Cc controls reject |
| Time | Exact int 1–60; bool rejects |
| Fixture files | 1–32 sorted unique allowed paths; differing before/proposed byte bodies; each <=65536 bytes, aggregate <=262144 bytes; UTF8, no CR/NUL; nonempty bodies end in LF |

The supplied accepted PR3-05 CanonicalContext is checked for exact project/task/
selected-step scope, exact repository source **and task binding**, complete closure
and currently byte/hash/size-consistent FROZEN or historically frozen SUPERSEDED
ArtifactContext. Context and nested task/selected artifact invariants are rechecked.
A projection supplied by a caller is not an unforgeable capability or a fresh
revocation check. This preview neither fetches context nor grants access, execution,
provider disclosure or scientific authority. Existing owning readers remain the
only source of real entitlement observations.

Fixture before/proposed bodies are arbitrary test data, **not proven extracted
from the repository artifact**. `fixture_repository_binding_verified=False`
remains mandatory even when the repository artifact's own bytes are consistent.
The workspace digest is a declared fixture label, not an observed checkout hash.

## Outputs and provenance

Result includes request scope/ref/workspace echoes and an engineering request
SHA256 over explicit canonical-json material. Raw fixture bytes are encoded as
lowercase hex; every field, NULL and empty tuple appears. This digest is not a new
scientific canonical hash scheme.

The unified diff is generated in memory from the exact fixture text with fixed
`a/path`/`b/path` headers, context=3, LF and no timestamps. LF byte-line splitting
preserves Unicode non-LF separators inside a line. Raw patch SHA256 and sorted
source candidates (path/proposed bytes/raw SHA256) are validated against the
original request; a self-consistent forged patch/hash alone does not pass.
Patch bytes are bounded at 524288. No patch is applied or written. Empty proposed
bytes represent a candidate empty file; no filesystem deletion is performed.

Configuration candidates, dependency-lock candidate and performed-command log are
empty/None. Test observation is always NOT_EXECUTED, skip reason
FAKE_PREVIEW_NO_EXECUTION, retaining exactly the declared tests. There is no PASS,
execution timestamp, exit status or fabricated stdout. Producer is pinned
`researchbase.fake-coding-preview` version `1`, provider FAKE, model None, runtime
IN_MEMORY_NO_SANDBOX and provenance UNVERIFIED. These are adapter identity labels,
not a production model/runtime lock.

Warnings always retain UNVERIFIED_PRODUCER, UNVERIFIED_FIXTURE_REPOSITORY_BINDING,
TESTS_NOT_EXECUTED, INDEPENDENT_SEMANTIC_ASSESSMENT_REQUIRED and
NO_FORMAL_ARTIFACT_VERSIONS. `semantic_impact=UNKNOWN` plus independent assessment
required are mandatory even for a syntax-only edit. All three scientific acceptance,
promotion and execution flags are exactly False. The adapter never writes an
Assessment, classifies its own edit NON_SEMANTIC, creates a Run, assigns formal
ArtifactVersion/AgentExecution IDs or accepts/promotes scientific state. Phase3
§§63–65 still require independent semantic assessment, defaulting uncertainty to
material for later owning acceptance.

## Remaining formal gates

- Accepted context has six input families; ExperimentSpecVersion is absent. No new
  family or invented execution context is supplied here.
- Generic gateway FakeParameters/mode/policy/consumer capabilities are unchanged.
  This preview is not wired to gateway/routing, APIs, CLI or task execution.
- Formal §10 outputs need actually registered ArtifactVersion IDs, owning source
  provenance and subsequent formal verification. These are not approximated by
  candidate hashes or unverified fixture labels.
- Real providers, credentials/egress, sandbox deployment, command execution, durable
  memory save, independent persisted SemanticImpactAssessment and acceptance each
  require their own authorized exact contract. This slice authorizes none of them.

No new canonical schema, migration, status, dependency, scientific identity or
architecture freeze is introduced. Bootstrap change admits exactly the three new
modules; existing recursive import and empty initializer restrictions remain.

## Validation

Meaningful tests cover literal deterministic diffs/hashes, exact/over-bound UTF8
and tuple sizes, malformed paths/control characters, wrong-scope denial, altered
frozen context/bindings/bytes, output tamper including forged consistent hashes,
mandatory false/fake/UNKNOWN/NOT_EXECUTED markers, request mutation and inert
instruction-like data. A real subprocess installs an audit hook rejecting file,
network, process and OS effect events before calling preview. No-effect source
import allowlist additionally rejects dynamic execution/effect dependencies.

Local evidence is retained outside the versioned source tree under
`.pipeline/logs/reviews/P04-fake-candidate-20261102/`; exact checks and final head
are reported there and in the PR. Initial relative-PYTHONPATH subprocess setup
failure is preserved separately and is not PASS. There is no local PostgreSQL
stage (`pg_argv=[]`); standard hosted required CI remains real and must pass at the
reviewed final head. No local test substitutes for a missing hosted check or
independent review.

Author-local validation at this candidate: 628 targeted/new/related pure tests passed
in 3.19s; whole-source/tests Ruff check and format passed (920 files); whole-source/
tests Pyright reported 0 errors, 0 warnings. These are author checks, not independent
review or hosted exact-head CI acceptance.
