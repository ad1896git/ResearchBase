# Immutable HEAD reconciliation

The authoritative PR-14R4 reviewed/final/current identity is the immutable
full commit SHA `724c67d4411fac7904470301cef80af18f1507a0`.

The PR-14R5 evidence payload commit is
`c75db39a3f712b39b7e8ce47eea3eb920bb30b86`. It is also the immutable
post-PR-14R5 current HEAD at payload capture. The later commit adding this R5
finalization package is a separate evidence commit and does not rewrite that
historical current-at-capture identity.

All authoritative reviewed/final/current identities are full immutable Git
commit SHAs. No authoritative identity delegates to a branch, tag, symbolic
name, external status report, null value, or token.

