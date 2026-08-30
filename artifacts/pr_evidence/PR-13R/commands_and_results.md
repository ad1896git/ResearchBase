# Commands and results

- PR-13/PR-13R targeted PostgreSQL: 13 passed.
- Full pytest: PASS; two inherited skips.
- SQL scaling: 15/15/15 SELECTs.
- Closure calls: 1/1, 1/9, 1/15 (Claim/Run).
- Ruff and Pyright: PASS.
- PostgreSQL 18.6; Alembic `0014_claim_evidence (head)`.
- Historical finalization inventory was replayed from Git for
  `ad5790c26dd26ef374ac96e36eb9283fc5604002..96fe5b203e23ed07fd212eb2be56dcc6e5318cc8`:
  exactly 3 modified PR-13R evidence files; source/test/migration count 0.
- Reviewed PR-13R HEAD: `96fe5b203e23ed07fd212eb2be56dcc6e5318cc8`.
