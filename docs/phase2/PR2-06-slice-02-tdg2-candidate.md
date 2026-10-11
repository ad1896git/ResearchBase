# PR2-06 Slice 02 — TDG2 candidate evidence (offline)

Retrieved official documentation on `2026-10-11T17:02:18Z` through read-only
documentation access. No Works API endpoint was contacted. This is a candidate
inventory, not a license determination or live-adapter admission.

## A. Provider, interface and pins

- Frozen TDG2-01 selects OpenAlex Works search. Adapter identity is
  `openalex` / local mapping `works-v1`; endpoint is the fixed HTTPS
  `https://api.openalex.org/works`. `works-v1` is **not** an upstream release pin.
- Pinned *local* interface at implementation commit
  `48cbce463d8237a08accbf366a4a611d065395d4`: first-page `GET /works`
  with `search`, bounded `per_page`, `page=1`, `select=id,title,doi,relevance_score`,
  optional date/language filters. Response projection is `meta.count`, optional
  `meta.page`/`per_page`, ordered `results[]` with `id`, `title`, optional `doi`
  and `relevance_score`, and optional request ID header. Unknown fields are data.
  Cursor traversal is outside this slice; a returned cursor is not followed.
- Synthetic offline fixture:
  `tests/fixtures/openalex_works_v1_offline.json`, SHA-256
  `dc39ef73028ba19ab73966463f7fb296cbd956974ac9d25bb3bc5f26fc155a9e`.
  Adapter SHA-256 `c9edf27c6eb8e7f09c047ecaa090a3219105290b1619208071addfbbecbebffe`;
  transport SHA-256 `f7f81098f107e39fdd89c730264e39c72a942eb117dc6a4fc1398bc29881464f`.
  `uv.lock` SHA-256 `e7155e4cbfe7f43157cba3f1c6fc0e7961f466d58810b09024f34487078b3ba6`.
  No new runtime dependency was added.
- Official interface references: [Works search](https://help.openalex.org/api/searching/),
  [paging](https://help.openalex.org/api/paging/), and
  [authentication/rate limits](https://help.openalex.org/api/authentication/).
  These pages are live documentation, not a fixed vendor API release. Their raw
  bytes and hashes were not available through this read-only retrieval.

## B. Licensing and attribution

- OpenAlex [dataset documentation](https://help.openalex.org/data/how-its-built/)
  describes its metadata as CC0. Its [Terms of Service](https://openalex.org/OpenAlex_termsofservice.pdf),
  revised `2026-10-02`, also impose service-access and use restrictions. The
  relationship between those statements for this deployment requires a separate
  rights review; no use or redistribution approval is inferred here.
- [Full-text documentation](https://help.openalex.org/access/fulltext/) states
  that PDFs keep their original copyright. A Work's metadata/license indication
  cannot itself authorize retention or redistribution of a linked publication.
  [License vocabulary](https://help.openalex.org/data/licenses/) includes
  location-specific and ambiguous categories. Unknown rights stay unresolved.
- Candidate attribution is provider `openalex`, adapter `works-v1`, normalized
  OpenAlex work ID, DOI URL when valid, ordered result rank, request ID when safe,
  and retrieval time. Exact attribution obligations under the current Terms
  remain for formal review. The fixture is synthetic and never retained science.

## C. Security and failure boundary

- Optional key enters the adapter from deployment configuration; it is sent in
  the Authorization header, not the URL or response DTO. The adapter never
  includes provider body/error text in `ProviderError`, and rejects a request ID
  that echoes the key. No key was committed or used in tests.
- Fixed HTTPS endpoint and no-redirect `literature_http.get_json` transport;
  no caller-selected host. The transport caps observed body bytes at 4 MiB.
  URL length is capped at 4094 UTF-8 bytes before dispatch. Proxy/DNS/egress
  policy and authorized access scope remain deployment activation checks.
- Adapter performs no retry. It classifies 401/403 as permanent, 429 and 5xx as
  retryable, carries bounded numeric `Retry-After`, treats transport ambiguity
  as `UNKNOWN`, and rejects cancellation before dispatch. The Application owns
  bounded retry and durable attempt provenance under TDG2-06/07.
- Explicit non-JSON content type, malformed JSON, invalid identifiers/DOIs,
  duplicate normalized IDs, wrong page metadata, oversize body, and schema
  drift fail closed. An incomplete response body is retryable with response
  received; other oversized/malformed bodies are permanent. Unknown fields
  cannot become canonical schema or instructions.

## D. Offline verification and unresolved activation gates

Run from this worktree with the existing Python 3.12+ environment used for verification:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'`

Result: **56 passed**. Ruff: all checks passed. Pyright: zero errors/warnings.
The exact three previously reported failures were rerun on both Slice 01 and
this candidate: two cancellation tests and the stale migration-list assertion
failed identically. They were not modified or reclassified as passing.

Formal TDG2 activation still requires a fixed upstream interface/version
inventory or approved compatibility pin, archived and hashed current provider
terms/docs, legal/access-scope decision, live-host egress and credential policy,
transitive lock/security review, timeout/rate-limit deployment settings, and
approved failure/compatibility evidence. The retained-M3 registry remains
disabled. M3 Human Gate remains blocked. No live provider, database, CAS,
scientific record, or human-verification evidence was touched.

## E. Slice 03 requirement matrix (candidate, not activation)

Reviewed official public pages at `2026-10-11T17:17:15Z` through read-only
documentation access. No Works API request was made. Candidate implementation
commit: `ed6edceaa91c0a116679dbcd06410873d224367c`. Local artifact SHA-256:

- `src/researchbase/adapters/literature_http.py`:
  `c09f104bdcf959cc2386473fd38c6d5360a05bc79abf8c66be3d1c046708f69d`
- `src/researchbase/adapters/openalex.py`:
  `27da1c7ec17888a91c7b31b9ba7c4a2a66e61945299d7d8bfab7473ccb8841dc`
- `tests/unit/phase2/test_pr2_06_transport_boundary.py`:
  `88dc2f9bfa917040f115f9a45d78b2bf56ee876d32b1d1999b473ba841fd500a`
- `tests/fixtures/openalex_works_v1_offline.json`:
  `dc39ef73028ba19ab73966463f7fb296cbd956974ac9d25bb3bc5f26fc155a9e`
- `uv.lock`: `e7155e4cbfe7f43157cba3f1c6fc0e7961f466d58810b09024f34487078b3ba6`

| Requirement | Authoritative source | Evidence / verification | Status |
| --- | --- | --- | --- |
| TDG2-01 OpenAlex Works discovery behind SearchCapability | `docs/architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md`; [OpenAlex search](https://help.openalex.org/api/searching/) | Fixed endpoint, local `works-v1` projection, offline fixture and adapter tests at candidate SHA; retained-M3 registration test. Live registration is separately unauthorized | REQUIRES_AUTHORIZATION |
| TDG2-02 Crossref DOI verification and noncanonical provider IDs | same frozen TDG2; `src/researchbase/adapters/crossref.py` | Normalization and M2 OpenAlex/Crossref regression tests; no canonical schema change | SATISFIED |
| TDG2-03 licensed full-text boundary | same frozen TDG2; [OpenAlex full-text licensing](https://help.openalex.org/access/fulltext/) | Adapter returns bibliographic candidates only; no PDF retention. Per-work rights decisions belong to a later full-text PR | UNRESOLVED |
| TDG2-04 scientific RAG adapter | same frozen TDG2 | Outside PR2-06; no PaperQA2 activation or dependency added | UNRESOLVED |
| TDG2-05 native STORM-like strategy | same frozen TDG2 | Outside PR2-06; no strategy change | UNRESOLVED |
| TDG2-06 bounded I/O, uncertainty, cancellation and provenance | same frozen TDG2; `src/researchbase/application/literature_search_execution.py` | Disconnected transport tests distinguish pre-dispatch, uncertain open, observed response, timeout, cancellation and secret-free error chains. Application execution tests: 16 passed; two separately listed baseline cancellation failures persist | UNRESOLVED |
| TDG2-07 rate limit and bounded retry | same frozen TDG2; [OpenAlex authentication/rate limits](https://help.openalex.org/api/authentication/) | Offline 429/5xx/401 tests, numeric `Retry-After`, no adapter retry; Application owns retry. Live quotas and deployment limits are unconfigured | REQUIRES_AUTHORIZATION |
| TDG2-08 cache policy | same frozen TDG2 | No cache introduced or retained response used; cache access-scope policy remains a later activation concern | SATISFIED |
| TDG2-09 credentials, egress, rights, and logging | same frozen TDG2; [OpenAlex key guidance](https://help.openalex.org/api/authentication/), [dataset CC0 statement](https://help.openalex.org/data/how-its-built/), [current Terms](https://openalex.org/OpenAlex_termsofservice.pdf), [full-text rights](https://help.openalex.org/access/fulltext/) | Synthetic-secret tests, fixed HTTPS host, no redirects, response cap, no raw exception chaining, request-ID allowlist. No real key or egress policy installed. Terms' service restrictions and CC0 statement need a rights decision; a metadata response grants no PDF rights | REQUIRES_AUTHORIZATION |
| TDG2-10 vendor-neutral canonical state | same frozen TDG2; `SearchCapability` port | Provider projection remains adapter-local; no schema, migration, canonical ID or scientific hash changed | SATISFIED |
| Live-adapter pin/access gate | final paragraph of frozen TDG2; [search](https://help.openalex.org/api/searching/), [paging](https://help.openalex.org/api/paging/), [auth](https://help.openalex.org/api/authentication/) | `works-v1` pins local mapping only. Public pages can change; raw upstream bytes/hashes and fixed upstream release/compatibility decision are not archived. `uv.lock` is pinned locally, but live access/security/license review is incomplete | UNRESOLVED |

The public pages above were inspected as references, not downloaded as
byte-for-byte archival artifacts. Their original SHA-256 values are therefore
**not verified**. A later authorized gate must archive exact upstream source
bytes, record retrieval and hash, resolve the CC0/Terms and attribution scope,
approve API access and secret injection, pin compatibility assumptions, and
approve egress, rate, timeout, retry and logging settings before registration.

Offline reproduction from this worktree (Python 3.12.14 environment used):

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'`

Result: 78 passed. The broader execution-service file has two identical
baseline/candidate cancellation failures; the legacy migration-list assertion
also fails identically on both. These are not passing tests or Slice 03 fixes.
No live provider credential, API call, retained scientific record, or M3
registration change was made. Formal TDG2 activation remains unauthorized.

Retained-state read-only check: two peer-authenticated `pg_dump --data-only
--no-owner --no-privileges researchbase_m3_retained_20261011` outputs, with
only pg_dump's generated `\\restrict`/`\\unrestrict` lines removed before
hashing, each had 23,890 bytes and SHA-256
`667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`.
Raw pg_dump stream hashes differ because those lines contain a random token;
they are not valid comparison evidence. The durable M3 CAS inventory before
and after evidence preparation has zero files and SHA-256
`2e9f267c0305f69e9abb2ca8b63bf0e30183e4e40ca26cd0e0bf06aebc5776bd`
over sorted relative paths, modes, sizes and content hashes. No retained M3
write was made. The data-only dump emitted PostgreSQL's existing circular-FK
restore warnings; this hash is an integrity comparison, not a recovery-backup
claim.
