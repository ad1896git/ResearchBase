# Route-to-Handler Map

| HTTP route group | Transport schemas | Accepted handler/query | Response DTO family | Errors |
|---|---|---|---|---|
| projects | `ProjectIn` | `ApplicationService.create_project` | `ProjectReadModel` | unified |
| research questions | `ResearchQuestionIn`, `ReviseResearchQuestionIn`, `FreezeResearchQuestionIn` | create/revise/freeze research question | research question read models | unified |
| hypotheses | `HypothesisIn`, `ReviseHypothesisIn`, `FreezeHypothesisIn` | create/revise/freeze hypothesis | hypothesis read models | unified |
| experiment specs | `ExperimentSpecIn`, `ReviseExperimentSpecIn`, `FreezeExperimentSpecIn` | create/revise/freeze experiment spec | experiment spec read models | unified |
| datasets | `DatasetIn`, `DatasetSnapshotIn` | register dataset/create snapshot | dataset read models | unified |
| artifacts | `ArtifactIn`, `ArtifactVersionIn`, `FreezeArtifactIn` | create artifact/version/freeze | artifact read models | unified |
| metrics | `MetricDefinitionIn`, `ReviseMetricDefinitionIn`, `FreezeMetricDefinitionIn` | create/revise/freeze metric definition | metric read models | unified |
| runs | `RunIn`, input/transition DTOs | create/attach/start/finish run | `RunReadModel` | unified |
| run provenance | path UUID | `ProvenanceQueryService.get_run_provenance` | `RunProvenanceDTO` | unified |
| measurements/statistics | measurement/statistical DTOs | record measurement/statistical result | accepted read models | unified |
| claims/evidence | claim/revision/evidence/freeze DTOs | create/revise/link/freeze claim | accepted read models | unified |
| claim trace | path UUID | `ProvenanceQueryService.trace_claim_to_runs` | `ClaimToRunsTraceDTO` | unified |
| governance writes | audit/impact/correction DTOs | accepted governance commands | governance records | unified |
| downstream impact | typed target + project query | `GovernanceQueryService.downstream_impact` | `DownstreamImpactTarget[]` | unified |

Direct repository routes: 0.
