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
  "success": {"status": 201, "response_keys": ["id", "name", "created_at", "row_version"]}
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
  "success": {"status": 200}
}
```

### Read and scientific provenance operations

```json
{
  "id": "read_run_provenance",
  "method": "GET",
  "path": "/v1/runs/RUN_ID/provenance",
  "success": {"status": 200}
}
```

```json
{
  "id": "trace_claim",
  "method": "GET",
  "path": "/v1/claim-versions/CLAIM_VERSION_ID/trace",
  "success": {"status": 200}
}
```

```json
{
  "id": "downstream_impact",
  "method": "GET",
  "path": "/v1/impact/artifact_version/ARTIFACT_VERSION_ID?project_id=PROJECT_ID",
  "success": {"status": 200}
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
  "failure": {"status": 422, "error_code": "VALIDATION_ERROR"}
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
