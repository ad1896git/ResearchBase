# Unresolved findings

P0: none.

P1: none.

P2: none.

P3: unreferenced content-addressed bytes after a failed DB transaction may remain until a
future garbage-collection policy; PR-07 explicitly permits this and does not require GC.
No PR-08 behavior is started.
