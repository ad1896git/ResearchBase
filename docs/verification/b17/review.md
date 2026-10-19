# Read-only independent review

> This is the historical source-inspection record, not a full-suite acceptance
> claim. Current post-review command results and the sandbox blocker are recorded
> in [implementation-evidence.md](implementation-evidence.md).

The root agent was the only writer. Separate agents investigated Application and
DDL dependencies read-only. A fresh-context independent reviewer read the approved
B17 proposal, authoritative design and diff, without authoring implementation.

P1 MAJOR: SQL freeze admission accepted finite timestamps before the transaction
started. A consistent package/event/receipt graph could therefore assert a
backdated freeze. The package seal and concrete freeze receipt guards now enforce
transaction-start lower bounds while retaining the shared observed advancing DB
time. The normal-role direct-SQL test asserts the exact rejection; the full
corruption matrix also includes backdating.

The reviewer inspected the correction and closed the P1. Their final inspection
reported no remaining P0/P1 implementation findings. They also identified two
test improvements: retain material after later review Issue insertion without
claiming scientific invalidity, and strengthen the SQL history regression. The
Issue assertion was corrected, and both the direct guard and otherwise complete
normal-role graph paths are tested.

The original race coverage gap was filled with observed both-order package,
maintenance, Issue INSERT/disposition and scientific invalidation tests, issuer
revocation/scheduled expiry and two-author consent-item rollback. Existing B16
dependency tests retain issuance/withdrawal empty-range coverage. Execution
counts are reported separately in implementation-evidence.md; this review record
does not turn unrun tests into PASS.
