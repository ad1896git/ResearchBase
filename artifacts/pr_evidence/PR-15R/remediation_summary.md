# PR-15R Remediation Summary

PR-15R changes tests and evidence only. Production adapter, Application, Domain, persistence,
schema, migrations, and dependencies are unchanged from reviewed PR-15 baseline
`1afe9845fb04cbbb243b290aecea84e6b74f1b0c`.

Committed test subject `6be2727669864da0e3a0d7b73dc2073068234d1f` adds real PostgreSQL HTTP writes,
fresh Application reads, direct-vs-HTTP write/query equivalence, the full recovery sequence,
three-route query purity and SQL counts, 35-route bindings, all-family runtime probes, malformed
transport coverage, complete stable-error mapping, and mixed request-ID concurrency.
