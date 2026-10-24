# ADR-0025 — PR3-03 architecture guard exception

Status: ACCEPTED — owner approved 2026-10-22. Exact pack §8 admissions only.

## Decision

Admit only source files listed as new in frozen pack §8 and DTO class names
defined there that contain "agent".
All paths below are relative to `src/researchbase/`, exactly as in the tests.
In `admitted_planning_files`, admit these seven runtime files from
[frozen pack §8](../../phase3/PR3-03-contract-freeze.md#8-closed-application-commands-dtos-and-gateway-port):

- `agent_runtime/domain/capability_invocation.py`
- `agent_runtime/domain/tool_policy.py`
- `agent_runtime/application/gateway_contracts.py`
- `agent_runtime/application/capability_gateway.py`
- `agent_runtime/application/routing.py`
- `agent_runtime/ports/capability_gateway.py`
- `agent_runtime/ports/gateway_repository.py`

Pack §8 also lists `persistence/capability_gateway_repository.py` and
`persistence/capability_gateway_queries.py`. These lie outside the runtime
scanner's namespaces and require no inventory exceptions; do not add ineffective
entries or expand scanner exclusions for them.

Admit exactly these (path, class name) pairs in the class-name guard:

- `agent_runtime/application/gateway_contracts.py`, `AgentExecutionContext`.
- `agent_runtime/application/gateway_contracts.py`, `AgentToolPolicyRead`.

No other exception is authorized. Preserve every pre-existing admission and
restriction. No whole-file class allowance, prefix match or namespace exemption
is added. Keep the negative test for unlisted classes and paths.
