# support_set_hash oracle report

The remediation oracle is test-local and black-box:

- production `semantic_row()` imported by oracle: NO
- production support-set material builder imported: NO
- production sorter imported: NO
- production support hash helper imported: NO

Literal expected rows used by the mixed vector include only:

```text
{"source_type":"measurement","source_id":"00000000-0000-0000-0000-000000000005","relation_type":"supports","qualification":null}
{"source_type":"measurement","source_id":"00000000-0000-0000-0000-000000000005","relation_type":"qualifies","qualification":"under the stated scope"}
{"source_type":"statistical_result","source_id":"00000000-0000-0000-0000-000000000006","relation_type":"context","qualification":"secondary analysis"}
```

The test independently sorts by source_type, source_id, relation_type, and NULL-first qualification, serializes with standard canonical JSON, and applies SHA-256. Independent expected hashes observed were:

- mixed vector: `9e82c63bfc28fd5823d27b56d1ff3d83861a569a483c07196a7e48148bd11cd9`
- same-prefix NULL/non-NULL vector: `1703ff12c28fa04ac2b84054a5cb13a1885409f33b5945dd323bb033dea75d4b`
- empty vector: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`

Single-variable tests change each semantic field and separately change relation identity, actor, timestamp, and insertion order. Semantic changes alter the hash; excluded metadata and order do not.
