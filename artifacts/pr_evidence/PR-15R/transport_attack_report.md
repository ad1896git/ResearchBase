# Transport Attack Report

Committed parameterized tests cover invalid path UUID, invalid body UUID, missing/invalid
`X-Actor-ID`, invalid `X-Request-ID`, invalid `X-Correlation-ID`, invalid `X-Causation-ID`, malformed
JSON, wrong enum, missing required field, wrong scalar type, and forbidden extra field.

Every case returns the normalized `VALIDATION_ERROR` envelope and records zero Application calls.
Mixed concurrent success/error requests also prove supplied request IDs remain request-local.
