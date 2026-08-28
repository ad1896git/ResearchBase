# FK RESTRICT report

Schema inspection found exactly three Measurement foreign keys, all with
ON DELETE RESTRICT, to runs, metric_definition_versions, and actors.
PostgreSQL integration attempts to delete referenced records were rejected. No
cascade is used on the scientific provenance chain.

Result: PASS.
