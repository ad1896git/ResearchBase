# Race-condition report

Reconciled by PR-09R: the original PR-09 concurrent-start/finish tests used independent sessions but no deterministic synchronization, and the original attach-vs-start statement was therefore overclaimed. PR-09R adds a `threading.Barrier` at the real Run lock path, proves both workers entered, records the final state, and verifies that no input edge commits after sealing. The original unsynchronized result remains historical evidence only.
