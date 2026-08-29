# Fingerprint reconciliation

All identifiers below were resolved with `git rev-parse` from the repository;
short forms are shown only in prose where useful.

## Historical chain

- Accepted PR-10 final baseline: `934e8690fc3f8459b1632e896f5c3be01abf8c1f`
- Reviewed PR-11 HEAD: `9592b66dc3372fae18fdd66555203f0788e407e2`
- PR-11R implementation/test commits:
  - `6319fda96e573e27ceca2afe1b45b03fcba5e628`
  - `13304196ba1f8d7044b92e1393a843debf35f974`
  - `4aa969e7781dd6fd36e7d98999153098af264095`
- PR-11R evidence commits:
  - `d95a0c15b63e848aaa7676832b11f400d932a85f`
  - `7e18e9283e4b416ccab250e9829eecf5f3e6f65f`
  - `5beb20c2ef0d75ff62eb7772b95289c84e57bff0`
  - `6675a7444cdb897d1bf810a55b32b6d88015ea15`
- Reviewed PR-11R HEAD: `6675a7444cdb897d1bf810a55b32b6d88015ea15`

## PR-11R2 chain

- Implementation/test commits:
  - `1e557818d1a2baa3f1929a7c2eb3c8f20a9a64e5`
  - `2304c081f668a01a7663624a271728431a9ba745`
- Evidence payload and final metadata commit SHAs are recorded in the final
  `harness_fingerprint.json` after each is resolved from Git.
- The final completion report separately records the post-evidence current
  HEAD, avoiding confusion between reviewed HEAD, payload commit, and current
  repository HEAD. The fingerprint's non-self-referential observation is the
  payload parent/current HEAD immediately before final metadata finalization.

## Inventory proof

The PR-11R historical inventory was checked with:
`git diff --name-only 9592b66dc3372fae18fdd66555203f0788e407e2..6675a7444cdb897d1bf810a55b32b6d88015ea15`.
The PR-11R2 inventory is regenerated from:
`git diff --name-only 6675a7444cdb897d1bf810a55b32b6d88015ea15..HEAD`.
The final evidence inventory is set-equal to the Git result.
