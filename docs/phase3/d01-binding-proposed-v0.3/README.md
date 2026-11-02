# D01 protected-binding contract candidate v0.3 — portable review bundle

**PROPOSED / NON-NORMATIVE / NO IMPLEMENTATION OR DEPLOYMENT AUTHORITY.**
This bundle packages an existing technical-consistency-reviewed candidate for
owner review. It does not freeze architecture, authorize D02 source implementation,
complete whole D01, select an actual host/budget/credentials or prove real PG18,
filesystem, permissions, factory wiring or lease safety. D01 stays HIGH and
owner-only; no E03 alias or automatic merge/admission is created. Owner must
explicitly freeze the exact contract through the proper approval path before use.

## Reading and precedence

Read repository AGENTS and its architecture read order first. Applicable authority
includes Phase3 development specification, the D1 amendment/current exact-boundary
packs, and existing installation/local-bearing source. This directory adds no
architecture/ADR/Harness amendment. Proposed technical details remain subordinate
to that authority; conflicts require an explicit review, never implicit precedence
from this file's presence in Git.

Start with [CONTRACT-PROPOSED.md](CONTRACT-PROPOSED.md), then the fixed-position
[codec specimen](generate_vectors.py), [SQL projection text](projection-PROPOSED.sql)
and [literal index](VECTOR-INDEX.md). The current candidate's 55 literal inputs are
stored as actual `.bin` files; [vectors.json](vectors.json) retains their full hex,
length/hash, decision time, expected binding hash and codec-only classification.
There are seven codec-only accepts and 48 rejects. Accepting a codec input alone
never approves a protected deployment record or any execution.

The v0.3 contract explicitly inherits unchanged v0.1/v0.2 portions. Both original
contract texts are therefore retained in [history/](history/) to make those
references inspectable without access to the operator's control directory.
Technical corrections in v0.3 (including v0.2 role/ACL/factory revisions) supersede
historical proposal details **within this proposed version only**; no historical
text or scientific authority is silently rewritten. Statements about a control
directory, line numbers, earlier source state, missing interfaces or original
review context are historical descriptions, not new checks of this Git head.
The full 18-position and nested typed grammar remains concretely inspectable in
the codec (AST-equivalent to the original; two long lines only are wrapped). The codec is a specimen, not a production verifier.

## Provenance and portability

[portable-manifest.json](portable-manifest.json) lists every bundled payload with
its relative path/hash and, for original snapshots, original repo-relative source,
original SHA256 and explicit transformations. The original v0.1/v0.2/v0.3 control
and review artifacts remain untouched outside this Git bundle. The original v0.3
manifest/review hashes are retained as provenance, not as an installed gate.

All 55 literal files, vectors JSON, SQL, contract and index bytes are copied
unchanged. The portable codec differs only in two long-line string/f-string wraps;
its AST is identical to the original (source locations excluded), and all 55
regenerated vectors remain byte-identical. No codec field or algorithm changes.
Only documentary metadata paths in catalog/sensitivity/review snapshots
lose the original personal checkout prefix; the historical distribution file path
becomes its basename. Headers, observations, semantic fields, decisions and hashes
are unchanged. No host catalog is read during this packaging or offline verification.
`local-catalog-source.json` is a historical distribution-header observation, not a
new database observation or approval of that installation. Fixtures use synthetic
values, including `/fixture/...`; those literal bytes must not be personalized.

The retained historical [independent technical review](history/D01-v03-technical-review.json)
reported PASS_PROPOSED_TECHNICAL_CONSISTENCY for the original v0.3, closing three
technical consistency findings. That review did **not** review this portability
commit, approve D01 architecture, pass an implementation or run PG/facilities.
This new bundle needs its own independent review of byte preservation, portability
and unchanged scope. Historical review hashes bind original bytes, not rewritten
metadata copies; compare the manifest's original and portable hashes explicitly.

## Pure offline reproduction

Use an already available **Python 3.12** interpreter (absolute interpreter path
recommended). No packages, network, DB, credentials or service are required:

```sh
python3.12 docs/phase3/d01-binding-proposed-v0.3/verify_bundle.py
```

The verifier checks all payload hashes and each literal's length, full hex, UTF8
rendering and SHA256. It copies only the AST-equivalent portable codec into an isolated temporary
directory and runs that specimen to regenerate vectors; the generated vectors JSON
and all 55 literal bytes must match the bundled originals byte for byte. The
original generator writes beside itself, so **do not run generate_vectors.py in
this committed directory**. The wrapper owns temporary files and cleans them up;
it does not modify the bundle or read the historical external paths.

A successful offline run means only reproducible specimen bytes/classifications,
not a production security validation. The helper is a documentation auxiliary,
never imported by business code, never installed in runtime and never a callable
startup/DB adapter. SQL is fixed proposed observation text and is **NOT RUN**.

## Gates that remain open

Owner exact contract freeze; actual operator-selected protected root/UID/DB/role/
endpoint/CAS/lease/record values and permissions; exact module-issued factory identity
and public-proof construction/consumption wiring; D02 implementation pack and real
PG18 negative tests; D03 thread/commit/revoke/cleanup lifetime and actual UoW binding;
any deployment or expanded topology/concurrency remain separate gates. Proposed
codec guard ceilings are not resource or billing budgets. No budget, host,
credential, schema, installation, registration, scientific acceptance or execution
is authorized by this bundle or a passing offline check.
