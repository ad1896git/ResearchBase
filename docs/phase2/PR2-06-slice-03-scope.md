# PR2-06 Slice 03 — transport error boundary and TDG2 candidate

Base: accepted Slice 02 evidence `9d67d643901539a73dec5c7b2663c4cd0ee86b16`.
This is conditional offline development. M3 Human Gate and live-provider activation remain blocked.

## Frozen implementation scope

- `literature_http.get_json` reports only observed dispatch/receipt certainty through a
  sanitized transport failure: local construction is `NOT_SENT`, an open failure
  without a response is `MAY_HAVE_BEEN_SENT`, and an observed response remains
  `RESPONSE_RECEIVED` even if its body is incomplete.
- `OpenAlexSearchCapability` maps those facts into existing provider codes. An
  arbitrary injected transport exception has unknown dispatch state. No raw
  exception or traceback cause crosses the provider boundary. Existing HTTP
  statuses, cancellation, response validation, and adapter identity remain.
- Deterministic disconnected tests prove certainty, retry safety, and secret
  non-disclosure. No network operation or retained data write is permitted.

## Evidence scope

Update the Slice 02 TDG2 candidate with a requirement-by-requirement evidence
matrix and explicit unresolved approval items. Official public documentation is
reference material only. No provider registration, credential installation,
schema/migration change, or scientific evidence promotion is in scope.
