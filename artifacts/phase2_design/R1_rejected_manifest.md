# Rejected Phase 2 R1 design snapshot

Base commit: `919c220f184242198d2cf4edb46ab9c163744a39`.

The eight R1 design files were uncommitted when R2 began. Git index writes were denied by this worktree sandbox; there is no committed R1 checkpoint in this repository. This patch preserves their exact bytes as a delta from the base commit. It is historical evidence, not an accepted design.

Patch SHA-256: `e133bc5fe064474853f827430cba2845ce2921e9378b6ff3d42219cd1e019df9`.

| Path | SHA-256 |
|---|---|
| `docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md` | `7637d56e1e9cef8d7e5b778959096f82dd73b81bd96c23466275eace7467a4c7` |
| `docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md` | `366c9922710e59b0364759f95d7af0184c90c71cbbfc8dcbc80c3eff63b58133` |
| `docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md` | `aae6c25e1da88c8c1783240959777a678112707322898634d8949d15368b210c` |
| `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md` | `8dad02342a8fe6729acc4add3085673a45104f4f903945b41c22344e7ef28776` |
| `docs/architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md` | `9b0f875f9fe42c3d684d8c59d84cbbb7d2fe63a97a3b984d536ebe8266b6c9c1` |
| `docs/architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md` | `de20f7c385203208185bf2604ba5c1c0db432b43420baf86cd53fe9c91141860` |
| `docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md` | `687c697403c473252bbc47d143d1abf12375d20f10e1141920d6fdef2d7658d1` |
| `execution/phase2/PR2-01_Design_Execution_Pack_v1.0.md` | `a5ec88a507f7cf753686ed8d320a9ee20cc28cc242dc1067cd4903c282337fa3` |

To reconstruct R1, apply the patch to a clean copy of the base commit. The R2 documents supersede R1 only through Addendum A18; this snapshot is not implementation authorization.
