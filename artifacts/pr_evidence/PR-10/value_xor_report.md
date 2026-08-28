# Value XOR report

Application and domain tests cover numeric-only, structured-only, both-null, and
both-present inputs. PostgreSQL integration tests directly exercise both invalid
insert shapes and verify the database check rejects them. Structured values are
limited to canonical JSON objects/lists; evaluation scope is nullable and, when
present, must be a canonical JSON object. Non-finite numeric values and unsupported
JSON values return VALIDATION_ERROR before persistence.

Result: PASS.
