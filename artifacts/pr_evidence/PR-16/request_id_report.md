# Request-ID Report

- Valid supplied request IDs reach the Application unchanged.
- Absent request IDs are generated once per invocation through the accepted UUID factory.
- Invalid request IDs receive one newly generated diagnostic request ID and exit 2.
- Error output always includes the request ID; JSON errors include it as `error.request_id`.
- Success, handled-error, transport-error, controlled-internal-error, and recovery sequences pass without
  cross-invocation request/context leakage.
