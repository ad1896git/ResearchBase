# ExecutionContext Report

The adapter maps `X-Actor-ID`, `X-Request-ID`, `X-Correlation-ID`, `X-Causation-ID`, `X-Client-Name`, and `X-Client-Version` exactly. `client_type` is `human_ui`. Missing required actor identity is transport validation; no authentication/IAM claim or fallback actor is introduced.
