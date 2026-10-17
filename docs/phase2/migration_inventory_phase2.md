Subject `1ae0036344c26057b1e70c7bbd3daf4e5d3b2d51`; dirty diff `f01f97fc03bf5cff9f3bfccfce2d46e7d2ef6121b0e820b363c8f6f8d336e47e`.

Machine evidence: [subject](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/subject.json). This is engineering evidence. Phase 2 exit is **BLOCKED**; owner acceptance is separate.

[Complete revision/predecessor/script digests](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/migration_scripts.json). No existing migration was edited; first-slice DDL and index proposals are empty. The historical inventory below originally ended at 0047; the integrated Batch D live head is `0059_b13_grant_consumption`. Owning legacy predicates and populated downgrade refusals remain authoritative. Empty/no-op, reconnect, accepted populated checkpoints, rollback and historical-manifest tests are separate evidence; absent checkpoint acceptance remains BLOCKED.

| Revision | Predecessor | SHA256 |
| --- | --- | --- |
| 0001_empty | None | e40c25c3b4b41bdf1a3831599b786f0d0f62800873f869a032382ba38df894f9 |
| 0002_actor_project_workspace | 0001_empty | 28cde30f786e3b629cf4553ac475518e5a13a381a4800a12f34817744f083dab |
| 0003_research_question_hypothesis | 0002_actor_project_workspace | 78e520d53634d9015cca6efdc5aab41ae55d61081e121f39bdf691837178a251 |
| 0004_experiment_spec | 0003_research_question_hypothesis | 8a16b3d1313e3eda2256626a32576e433775fd1542a858bb4c3115efd3139697 |
| 0005_dataset_snapshot | 0004_experiment_spec | bde5ee8a193dfd42259e0b7484c0450467490e40dab1dc304b18cea082144736 |
| 0006_artifact_version | 0005_dataset_snapshot | 5de0531212cfd5322294b7e1736a4d331a2c9a9ee979fb09ab083e01e439dd9f |
| 0007_metric_definition | 0006_artifact_version | a1325daea0623becab05a4e55d52c0a796f477f921d41e5a40e326a7f916a5d2 |
| 0008_run_core | 0007_metric_definition | fb4f03493ded0d3ba168a5fe413be4f330e01bc21a48148e1cfa8fdb9636ffe6 |
| 0009_run_input_seal_fix | 0008_run_core | 75a04a25c3b7b46677bd5b3c49e0f84955df5437a0b20ab202ff3f50e012a09f |
| 0010_measurement | 0009_run_input_seal_fix | 962e9928f5c604865e0d6b8d8178439f81016cafbdba15520175f2f046843405 |
| 0011_statistical_result | 0010_measurement | ddb6b29cc20343e5bc1d179a3bb68862bc32206dbdc31e7cd818cfcaba569b7f |
| 0012_statistical_result_input_guard | 0011_statistical_result | 7b11676e5b92149693f9b7ff8ee3f86bacc5d2bae3e91ec0a551def323583a5d |
| 0013_statistical_result_legacy_input_precheck | 0012_statistical_result_input_guard | ab47bfb02493a58a47cb41485bd02cd91b19b9737c45be97623df1ec495c9a9a |
| 0014_claim_evidence | 0013_statistical_result_legacy_input_precheck | 71a60f4f565e94dda91db5e87e00ae3b3146b6ea4d91f5324d67b8c9cf713718 |
| 0015_governance_audit | 0014_claim_evidence | c8e138423c4d4f180c18a6a262f503a478eb540f2317861ee40c9da23163b073 |
| 0016_pr17d_history_protection | 0015_governance_audit | 4bee1a77319d0462fee9731dc68b637f55e93c7fe8ab5da1675f7ad44cd3c41f |
| 0017_persisted_canonical_enum_normalization | 0016_pr17d_history_protection | 8885a1aee20f6583c2267ae845ada7314597d7048f868db0bcef85f12a78f3a7 |
| 0018_current_pointer_same_parent_integrity | 0017_persisted_canonical_enum_normalization | 91c4ddfd54c08ee4b0607474e3b9699a3b04ab66a7272d3e7c309ae894c5dbaf |
| 0019_phase2_bootstrap_membership | 0018_current_pointer_same_parent_integrity | 5cd033b7db3e7fd1f734be74f2b104169a26fd9abc4b659e7f25415ab9e94b35 |
| 0020_literature_source_identity | 0019_phase2_bootstrap_membership | d7d9d9c7af64f79cb69de90358d4769d7dd93f6a8a9d7d835be22bc9c2f543dd |
| 0021_source_merge_governance_bridge | 0020_literature_source_identity | 90e0bc77a14716455bdcd73ab855ade00a2d39884008b245974a6ea0a06152f2 |
| 0021a_source_merge_gov_guards | 0021_source_merge_governance_bridge | c6a4a9d8784bef2cfe90ac9b9bbae628d93e9dfef944a7ed3eb7f4ceccf671e1 |
| 0022_source_version_and_merge_lineage | 0021a_source_merge_gov_guards | ecb967f6a46f5ecac66f1133a48a2aa8fcb2170d39b20d521db0de3e3f60eeca |
| 0023_literature_search_plan | 0022_source_version_and_merge_lineage | b45efd54000766b927e288aacc875f60867bed2df4f3d125e58e1d835e938667 |
| 0023a_search_plan_review_guards | 0023_literature_search_plan | b9306a4fc063276f0e37e70c41448319d02db2507350e9c80c1d39b7a692c860 |
| 0024_literature_search_execution | 0023a_search_plan_review_guards | 7492edc479a1b4117f4581fd5c1b72157abb07d8e633558b911e08d02a06f7b2 |
| 0025_pr2_04_reservation_guards | 0024_literature_search_execution | 352a7a088e935ac937075f748447439dde090af2bc8d52aeb750ee207df77ad0 |
| 0026_pr2_04_p1_contract_guards | 0025_pr2_04_reservation_guards | 35502cf80dd085369f6a7ab627ef6053e13ee9c14256239794dfca8590e1f9ca |
| 0027_pr2_04_hash_scheme_guards | 0026_pr2_04_p1_contract_guards | cc0dccc6ebbae41b70b014ff99b9bdcc16e44e11f5b95af329cabd44a816a269 |
| 0028_provider_cancellation | 0027_pr2_04_hash_scheme_guards | 761d175f0abdc3e0bcd75874222d36313b369f4f7047b94b801fc8aa42311a34 |
| 0029_metadata_observations | 0028_provider_cancellation | 42ce605f81996330116968e9c6119855022d495d56d47a6406da923a36c7467e |
| 0030_literature_evidence | 0029_metadata_observations | f541fa5a5d9ec00752f3af3d20d8e33f1b5981568296664d098db4c56b76403c |
| 0031_m3_snapshot_relation_cardinality | 0030_literature_evidence | bfd387b9ff5bef5b53c39acdcac04d3f5371981a2f766861fa85cff05f624921 |
| 0032_pr2_10_discussion | 0031_m3_snapshot_relation_cardinality | 115646bf64c8f9a8bb98947f1a26a4b2223ae4f889702b2ed406813dcc2589f7 |
| 0033_pr2_11_r2_scientific_conclusion | 0032_pr2_10_discussion | f0040ca50208a2b5db9f625182e1bdbb8775db0a128969d7415315d6c3f9c7ef |
| 0034_pr2_10_exact_transcript_binding | 0033_pr2_11_r2_scientific_conclusion | 8973ed9869897347a2036d6385d649a4841030033f2d25414a1d3ab763bde4e7 |
| 0035_pr2_12_publication_draft | 0034_pr2_10_exact_transcript_binding | e2edbfd14e243a057f10b93500796a945e49b66fb84b74321464dc942c9bbbbb |
| 0036_pr2_13_citation_placement | 0035_pr2_12_publication_draft | e8a6b1ca24988f5353907aa66e56699cd9d000f3a73b04d2e4e369ba613f7887 |
| 0037_pr2_13_claim_placement | 0036_pr2_13_citation_placement | 804e7195c0333168f839f7f8944a170f68f9797407969bb9e1a7e9fe5e4edbb1 |
| 0038_pr2_13_artifact_placement | 0037_pr2_13_claim_placement | fa21eeb80352de56715c035693b04bd41da8cf6a1bfde27ddae9fc8f43cbc150 |
| 0039_pr2_13_citation_rebinding_guard | 0038_pr2_13_artifact_placement | c205b0a265ca953b7fb9314d2bc3532c070c6b1e3f81f25757ddbb8651e9adbf |
| 0040_pr2_14_initial_internal_review | 0039_pr2_13_citation_rebinding_guard | 5cfb790aa6afd1d1685612be064715736ac94a9aea3a91d69881d4d94f3bc25f |
| 0041_pr2_15_review_coordination | 0040_pr2_14_initial_internal_review | 25fbc0f7a662cc8f625f66896378402376b4a9b8f37c1c464408291b8a803c44 |
| 0042_pr2_15_minimal_decision | 0041_pr2_15_review_coordination | 8a61d6714b6f7a05cd87d6a4ac95f5cf7eb9d5b0fc7e21d1e7522f31aa73e312 |
| 0043_pr2_04_schema_contract | 0042_pr2_15_minimal_decision | 7ddd69ac5283ec6b5ab76ae3076873b6d1ab12b8946bb2e317d9a44f0be71ed2 |
| 0044_pr2_15_revision_action | 0043_pr2_04_schema_contract | c1885dea62e2564c9e53fc804c77fa909d0a2b2c075b06d550eee2a0fd2863d0 |
| 0045_pr2_16_basic_approval | 0044_pr2_15_revision_action | 19fb8d0ba3af38347d293ffb3e478cddbef5c5047b41d49a8e1c49ed8323d187 |
| 0046_pr2_17_authorship | 0045_pr2_16_basic_approval | bac73fbe714985a83a385712e91b56bfe5ba46f0b45327e97a158b22da0f1f65 |
| 0047_pr2_18_novelty_prior_art | 0046_pr2_17_authorship | a58e2d44d9ee502a7906a92749db28923d2550ba843bb83ea1a64b2fbe4defde |
| 0048_b04_manuscript_freeze | 0047_pr2_18_novelty_prior_art | 8dc9b61712aaf6fb02513ece31f12642e4fce7a8e8df947985e8346c85a43660 |
| 0049_b05_manuscript_review | 0048_b04_manuscript_freeze | 7af4310b3a39f2bd64556a51ebd9723c28d86f0a926e1a239fc0ecf03c93bee5 |
| 0050_b01_resolution_admission | 0049_b05_manuscript_review | 101fc8c7a1408397234854c2f714e3da656c57c369f4bfa1b9d5e259a8614f69 |
| 0051_b06_revision_action | 0050_b01_resolution_admission | 004a272db75d945c10e9e6e318c106f47b2cb37c1421ff75f99240312490ca46 |
| 0052_b07_revision_decisions | 0051_b06_revision_action | 3b3e6048452ed702771278dd76a85f1a92e90245726198fc49678e4da9848c6c |
| 0053_b08_issue_disposition | 0052_b07_revision_decisions | ac93a13b17aa6872230bbf831613c2775cf382e81ce1d64774106f8f628b2b63 |
| 0054_b11_ready_for_submission | 0053_b08_issue_disposition | b1ea6609e911b36f1d86adba9697b213ae8ebaa1ce7e70de8da80e7c2e2c6c75 |
| 0055_b09_approval_tuples | 0054_b11_ready_for_submission | 449e624dc4d420bd5c625e065d6f60e9f24d132bcd25483bd5de774e46013057 |
| 0056_b10_reconsideration | 0055_b09_approval_tuples | d17c42a19b99c575a767dd12159ec7eeeb651ede7577c98958e8ed90ec9f346f |
| 0057_xid_wraparound_guards | 0056_b10_reconsideration | 0da197d0b8ca619925813d5b26cf43c4646eeb5bbe18b64a4f3b9bfaf3e34e3b |
| 0058_b12_prepare_submission | 0057_xid_wraparound_guards | 0b3cbf0a62dd86253d6b4c313c2ca5f3ff68547013ddb1916f24317974aec043 |
| 0059_b13_grant_consumption | 0058_b12_prepare_submission | f63eaf66f359761afd37a7299595cfa6de4972ca5cf53cd2bdc6c79b251d6350 |

Owner remediation decision, 2026-10-17: apply the proposed B10 compatibility fix
and remove the unrequested 0054a/0057 workaround migrations. The final chain is
B11 → B09 (0055) → B10 (0056). B09 SQL constants match lane 13 byte-for-byte.
B10 retains the B07/B11 finite pairs and typed basis dispatch, uses B11's existing
constraint name on upgrade, and restores the B11 policy/dispatch on downgrade.
No dummy CHECK constraints, new canonical schemas, or alternate history remain.
Full-schema downgrade comparison and source-lane SQL diffs are recorded in
[Batch C evidence](../verification/batch-c/integration-evidence.md).

Batch D integration, 2026-10-17: B12/B13 retain their existing linear parents
0057 → 0058 → 0059, with byte-identical migration files and DDL. B25 has no
migration. The empty B27 revision was removed by owner instruction; defensive
reads require no schema change. B14 remains deferred. No new PR2-20 evidence
directory was generated. Focused verification is recorded in
[Batch D integration evidence](../verification/batch-d/integration-evidence.md).
