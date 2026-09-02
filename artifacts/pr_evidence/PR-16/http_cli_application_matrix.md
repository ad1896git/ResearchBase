# HTTP / CLI / Application Matrix

| Use-case family | PR-15 HTTP adapter | PR-16 CLI adapter | Shared Application boundary |
|---|---|---|---|
| project | POST `/v1/projects` | `project create` | `create_project` |
| research question | frozen create/revise/freeze routes | `rq create/revise/freeze` | corresponding handlers |
| hypothesis | frozen create/revise/freeze routes | `hypothesis create/revise/freeze` | corresponding handlers |
| experiment spec | frozen create/revise/freeze routes | `spec create/revise/freeze` | corresponding handlers |
| dataset/artifact/metric | frozen create/version/freeze routes | `dataset`, `artifact`, `metric` groups | corresponding handlers |
| run | frozen create/input/start/finish routes | `run create/add-dataset/add-artifact/start/finish` | corresponding handlers |
| provenance | GET run provenance | `run provenance` | `ProvenanceQueryService.get_run_provenance` |
| measurement/statistics | frozen write routes | `measurement create`, `stats create` | corresponding handlers |
| claim/evidence | frozen write routes | `claim create/revise/add-evidence/freeze` | corresponding handlers |
| claim trace | GET claim trace | `claim trace` | `trace_claim_to_runs` |
| governance | frozen audit/impact/correction routes | `audit`, `impact`, `correction` groups | governance services |
| downstream impact | GET impact | `impact show` | `downstream_impact` |

CLI-only business semantics: none. Direct repository/ORM orchestration: none.
