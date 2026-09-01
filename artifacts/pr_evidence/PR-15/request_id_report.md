# Request ID Report

- Valid canonical `X-Request-ID`: preserved exactly.
- Missing ID: generated once using `new_uuid7`.
- Invalid/non-canonical ID: normalized 422 with a generated response ID.
- Success, handled error, validation error, and controlled 500 responses carry `X-Request-ID`.
- 32 concurrent generated-ID requests produced 32 distinct IDs.
