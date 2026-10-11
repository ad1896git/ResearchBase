# PR2-08 conditional slice 01 — deterministic native strategy candidate

**Base:** reviewed conditional PR2-07 evidence
`2a1cd6d6648135893d20062572e52facbab20a42`.

**Frozen sources:** Phase 2 spec §§8–9, 35, 41.5, 55.1–55.2 and PR2-08;
TDG2-05/10; Cross-Phase Contract §20. A ResearchBrief is an ArtifactVersion
role, not a new canonical entity.

**Scope:** Implement the provider-neutral `ResearchStrategy.prepare_plan` /
`execute` boundary and one deterministic native baseline. Prepare three
bounded perspectives (methods, findings, limitations) and corresponding
queries from a topic. Execute against an injected ScientificRAGCapability
limited to exact requested SourceVersion IDs. Return typed unverified
source/evidence candidates, a ResearchBrief **candidate** with exact source
locators and query/provider provenance, open questions, coverage limitations
and safe warnings. A provider failure must not fabricate a section answer.
Cancellation aborts without a partial result. No canonical promotion occurs.
The Application caller constructs `ResearchStrategyContext` from the original
authorized request. Execution compares the full plan with that trusted request
before dispatch; a plan cannot authorize its own source set. The context is
not a caller-supplied authorization object. Provider contradiction and missing
evidence notes stay in the unverified section candidate and suppress an
unqualified answer candidate.

**Exclusions:** No live search/RAG/model call, PaperQA2/STORM package,
retained database/CAS write, ArtifactVersion creation, scientific schema or
hash change, hypothesis promotion, synthetic human review, or formal PR2-08
acceptance. The full later strategy integration must persist queries and the
ResearchBrief through authorized Application commands before admission.

**Acceptance:** Deterministic plan order, source-set and query binding,
source-grounded section candidates, provenance/coverage limits, provider
failure isolation, cancellation, and no fabricated unverified facts. Focused
tests plus M2/M3 regression, architecture, Ruff and Pyright checks.

**STOP:** Any need for retained write, new canonical schema, live provider,
unverified human authority, or a PR2-07 adapter admission that is not held.
