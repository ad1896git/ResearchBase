# FK RESTRICT report

Reconciled by PR-09R: PostgreSQL constraint inspection confirmed seven PR-09 foreign keys with `ON DELETE RESTRICT`. The original PR-09 behavioral coverage attempted only Run deletion, so its broader implication was incomplete. PR-09R attempts deletion of Project, ExperimentSpecVersion, Actor, DatasetSnapshot, ArtifactVersion, and Run with attached inputs; every delete is rejected and fresh reads prove survival.
