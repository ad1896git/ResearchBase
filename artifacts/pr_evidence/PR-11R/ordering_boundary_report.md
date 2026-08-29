# Ordering and boundary report

The input query orders by `ordinal ASC, input_role ASC, measurement_id ASC`.
Two inputs with the same ordinal and role were inserted in reverse UUID order;
the fresh query returned Measurement IDs in ascending UUID order, proving
insertion-order independence.

Domain and PostgreSQL boundary coverage observed:

- `input_role` length 32: accepted;
- empty `input_role`: rejected with `VALIDATION_ERROR`;
- length 33 `input_role`: rejected with `VALIDATION_ERROR`.
