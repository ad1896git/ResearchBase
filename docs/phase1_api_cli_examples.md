# Phase 1 API and CLI examples

These examples use only the finalized Phase 1 transport surface. They are
illustrative requests: identifiers are placeholders and must be replaced with
UUIDs from the same project.

## HTTP API

Create a project through the Application-backed API:

```bash
curl -sS -X POST http://localhost:8000/v1/projects \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-ID: 00000000-0000-0000-0000-000000000001' \
  -d '{"name":"example-project","description":"Phase 1 example"}'
```

Read exact run provenance, claim-to-run trace, and downstream impact:

```bash
curl -sS http://localhost:8000/v1/runs/RUN_ID/provenance
curl -sS http://localhost:8000/v1/claim-versions/CLAIM_VERSION_ID/trace
curl -sS 'http://localhost:8000/v1/impact/artifact_version/ARTIFACT_VERSION_ID?project_id=PROJECT_ID'
```

Unexpected server failures return the stable `INTERNAL_ERROR` envelope and do
not include exception text or credentials.

## CLI

The CLI uses the existing deterministic JSON output mode:

```bash
researchbase --actor-id ACTOR_ID project create --name example-project --json
researchbase --actor-id ACTOR_ID run provenance --run-id RUN_ID --json
researchbase --actor-id ACTOR_ID claim trace --claim-version-id CLAIM_VERSION_ID --json
researchbase --actor-id ACTOR_ID impact show \
  --project-id PROJECT_ID \
  --target-type artifact_version \
  --target-id ARTIFACT_VERSION_ID \
  --json
```

Stable semantic errors are written to stderr with a code and request id; raw
stack traces and database details are not part of the CLI contract.
