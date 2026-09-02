# Input Validation Report

The transport attack matrix passed for invalid UUID arguments/options, invalid actor/request/correlation/
causation IDs, malformed JSON, missing and malformed JSON files, wrong enum values, missing required fields,
wrong scalar types, invalid artifact base64, and unexpected options.

Transport failures are raised before the Application handler. They use exit 2, include one request ID, and in
JSON mode write one JSON error document to stderr with empty stdout. JSON-file input is read only from the
specified UTF-8 path; no globbing, recursion, shell execution, or input-file mutation exists.
