# Failure Recovery Report

The HTTP and Typer sequences each pass independently:

`valid write → handled ResearchBase error → valid query → transport validation error → valid write/query → controlled unexpected adapter error → valid query`.

HTTP maps handled errors to its stable envelope and status; unexpected errors return the generic 500 response.
Typer maps handled errors to the stable exit code and request ID; unexpected errors return exit 70 and the generic
message. No raw psycopg/SQLAlchemy detail or traceback appears in public output.

The next operation succeeds after each error. Request IDs are supplied per invocation in the test and are not
reused by adapter state. Existing PR-16 transport and recovery tests also pass.
