# Phase 1 API and CLI examples

These examples use only the finalized Phase 1 transport surface. They are
illustrative requests: identifiers are placeholders and must be replaced with
UUIDs from the same project.

## HTTP API

The following machine-readable contracts are the source for the executable
documentation checks in `tests/unit/test_pr18_docs_examples.py`. UUID tokens
are placeholders; replace them with identifiers from the same project.

### Create a project

```json
{
  "id": "create_project",
  "method": "POST",
  "path": "/v1/projects",
  "request": {"name": "example-project", "description": "Phase 1 example"},
  "success": {"status": 201, "response_keys": ["id", "name", "created_at", "row_version"], "identifier_semantics": "canonical project id"}
}
```

```bash
curl -sS -X POST http://localhost:8000/v1/projects \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-ID: 00000000-0000-0000-0000-000000000001' \
  -d '{"name":"example-project","description":"Phase 1 example"}'
```

### Version transition

```json
{
  "id": "freeze_artifact_version",
  "method": "POST",
  "path": "/v1/artifact-versions/ARTIFACT_VERSION_ID:freeze",
  "request": {"artifact_id": "ARTIFACT_ID", "expected_row_version": 1},
  "success": {"status": 200, "response_keys": ["id", "artifact_id", "status", "content_hash", "row_version"], "identifier_semantics": "the path id is the frozen artifact-version id"}
}
```

### Read and scientific provenance operations

```json
{
  "id": "read_run_provenance",
  "method": "GET",
  "path": "/v1/runs/RUN_ID/provenance",
  "request": {},
  "success": {"status": 200, "response_keys": ["run_id", "project_id", "status", "closure"], "identifier_semantics": "RUN_ID is the canonical run id"}
}
```

```json
{
  "id": "trace_claim",
  "method": "GET",
  "path": "/v1/claim-versions/CLAIM_VERSION_ID/trace",
  "request": {},
  "success": {"status": 200, "response_keys": ["claim_version_id", "project_id", "runs", "paths", "closure"], "identifier_semantics": "CLAIM_VERSION_ID is the frozen claim-version id"}
}
```

```json
{
  "id": "downstream_impact",
  "method": "GET",
  "path": "/v1/impact/artifact_version/ARTIFACT_VERSION_ID?project_id=PROJECT_ID",
  "query": {"project_id": "PROJECT_ID"},
  "success": {"status": 200, "response_type": "array", "identifier_semantics": "PROJECT_ID scopes ARTIFACT_VERSION_ID to one project"}
}
```

The equivalent requests are:

```bash
curl -sS http://localhost:8000/v1/runs/RUN_ID/provenance
curl -sS http://localhost:8000/v1/claim-versions/CLAIM_VERSION_ID/trace
curl -sS 'http://localhost:8000/v1/impact/artifact_version/ARTIFACT_VERSION_ID?project_id=PROJECT_ID'
```

### Failure contract

```json
{
  "id": "create_project_failure",
  "method": "POST",
  "path": "/v1/projects",
  "request": {"description": "missing required name"},
  "failure": {"status": 422, "error_code": "VALIDATION_ERROR", "error_response_keys": ["error"], "error_shape": ["code", "message", "details"]}
}
```

Validation and unexpected server failures use the stable `error` envelope and
do not include exception text or credentials.

## CLI

The CLI uses the existing deterministic JSON output mode:

```json
{
  "id": "project_create",
  "command": ["--actor-id", "ACTOR_ID", "project", "create", "--name", "example-project", "--json"],
  "success": {"exit_code": 0, "output": "json"}
}
```

```json
{
  "id": "run_provenance",
  "command": ["--actor-id", "ACTOR_ID", "run", "provenance", "--run-id", "RUN_ID", "--json"],
  "success": {"exit_code": 0, "output": "json"}
}
```

```json
{
  "id": "claim_trace",
  "command": ["--actor-id", "ACTOR_ID", "claim", "trace", "--claim-version-id", "CLAIM_VERSION_ID", "--json"],
  "success": {"exit_code": 0, "output": "json"}
}
```

```json
{
  "id": "impact_show",
  "command": ["--actor-id", "ACTOR_ID", "impact", "show", "--project-id", "PROJECT_ID", "--target-type", "artifact_version", "--target-id", "ARTIFACT_VERSION_ID", "--json"],
  "success": {"exit_code": 0, "output": "json"}
}
```

```json
{
  "id": "project_create_failure",
  "command": ["--actor-id", "ACTOR_ID", "project", "create", "--json"],
  "failure": {"exit_code": 2, "output": "usage-error"}
}
```

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
