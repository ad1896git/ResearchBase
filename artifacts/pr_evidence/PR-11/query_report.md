# Query report

The application exposes:

- `get_statistical_result`;
- `list_statistical_results_for_project`, ordered by `created_at ASC, id ASC`;
- `list_statistical_result_inputs`, ordered by `ordinal ASC, input_role ASC,
  measurement_id ASC`.

The adapter uses SQLAlchemy Core table selections and maps rows to frozen
application DTOs. Integration tests verified project isolation, deterministic
ordering, exact input ordering, historical IDs, and absence of ORM state on
returned objects.
