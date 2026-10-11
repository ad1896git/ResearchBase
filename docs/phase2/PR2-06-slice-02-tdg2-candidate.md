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

Run from this worktree with the existing project virtual environment:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'`

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
