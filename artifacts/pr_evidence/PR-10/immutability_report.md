# Immutability report

The Measurement repository exposes only add/get/list operations; no update, save, or
delete surface exists. The frozen domain record is a dataclass. PostgreSQL trigger
measurements_immutable rejects direct UPDATE and DELETE. Integration tests attempted
updates to every Measurement column and direct deletion; each was rejected and the
original row remained present.

Result: PASS.
