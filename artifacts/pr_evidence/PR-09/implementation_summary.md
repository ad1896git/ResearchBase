# PR-09 implementation summary

PR-09 implements Run Core only. It adds the framework-neutral `Run` aggregate, closed dataset/artifact input roles, application commands, repository/UoW ports and SQLAlchemy adapters, migration `0008_run_core`, and `ProvenanceClosureValidator` v1.

Accepted PR-08 baseline `275de41` is preserved. Implementation commits are `532a350` and `17a5f66`. No RunVersion, Measurement, StatisticalResult, Claim, or later-phase implementation was added.
