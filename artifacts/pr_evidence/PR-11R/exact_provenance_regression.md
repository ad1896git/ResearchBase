# Exact provenance regression

The regression created MetricDefinitionVersion V1, froze it, created
Measurement M1 against V1, and recorded StatisticalResult S against M1. A
new version V2 was then created and frozen, causing V1 to become SUPERSEDED.

After the state advance, a new UoW returned:

- S's exact input Measurement ID: M1;
- unchanged input role and ordinal;
- unchanged StatisticalResult row values;
- unchanged content hash.

No current/latest lookup contaminates the historical edge.
