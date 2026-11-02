# E04 throughput execution pack

This engineering-only change implements the authorized C throughput slice on base
`4ad4e834098b6bf111779752b897b00787a9dede`. Risk is **high**: admission authority,
resource ownership and crash recovery change together. Owner approval and all seven
exact-head checks are required. This PR does not deploy or change branch settings.
No scientific schema, canonical write path or business group changes.

The runtime may scan an owner-frozen authorization/gate index, create minimal
execution packets and queue already authorized implementation/audit work. A reusable
closed template supplies stage roles and an optional fixed host pytest command;
operators do not prepare per-task jobs/stages. Each task still needs its actual
frozen specification, scope and gate evidence. Missing contracts, owner-only tasks,
unknown types/risks, unmet dependencies and revoked authorization must be visible
holds or blocks. Model answers cannot authorize work, declare whole-BACKLOG
completion or create a publication capability.

Required verification: persisted CI pending/success/timeout/retry and query failures;
actual lease release across probes; real independent work while CI waits; capability
negative cases; distinct read-only review checkout; host-derived source commit with
original model receipt preserved; actual candidate-source imports and full archive;
resource quarantine on uncertain descendants; policy revision and lost-state guards;
PG identity pins and nonempty, zero-skip test acceptance. Run all pipeline regression
tests, Ruff, Pyright and exact diff checks. Retain raw observations and failed setup
attempts; never turn missing execution into PASS.

The existing main publication deny remains. Generated work ends at
`awaiting_publication`; E03/owner must supply an approved published exact-head PR
binding before existing CI/approval/merge processing can consume it. This is not
unattended completion of every BACKLOG parent. Deployment requires a separate
owner-authorized rollout and independent review.
