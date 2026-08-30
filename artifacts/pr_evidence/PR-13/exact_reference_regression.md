# Exact-reference regression

Implementation inspection confirms all traversal begins from concrete FK values already stored on
Run, EvidenceRelation, StatisticalResultInput, and Measurement. No call to any `get_current_version`
or latest-selection method exists in the PR-13 query module. Historical SUPERSEDED versions are not
filtered. Focused tests assert the exact IDs created by the fixture.

