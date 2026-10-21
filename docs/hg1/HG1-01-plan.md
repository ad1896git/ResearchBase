# HG1-01 Minimal Local Trusted Runner Implementation Plan

**Goal:** Add a short-lived macOS Unix-socket Runner for the existing trusted Local-First M2 deployment without changing scientific or identity contracts.

**Architecture:** The non-root `onephone` process retains the existing installation, peer-authenticated PostgreSQL and CAS access. A framed client sends only versioned operation data. The Runner derives peer UID/GID with macOS `getpeereid(2)`, requires the deployment owner's UID, then delegates authentication and project authorization to the existing Application composition. Other UIDs fail closed; enrollment is outside HG1-01.

**Tech stack:** Python 3.12 standard library, existing ResearchBase Application/CLI composition, PostgreSQL 18.6 through the existing Unix socket.

## Bounded tasks

- [x] Create isolated worktree at accepted M3 commit; verify clean baseline.
- [x] Test-first protocol, kernel peer credential, principal-mapping and socket lifecycle behavior.
- [x] Implement `src/researchbase/runner.py` with two read-only operations and strict deployment settings.
- [x] Add and run read-only four-deployment live integration test.
- [x] Compare all 256 M2 public-table canonical hashes with the frozen baseline.
- [x] Record final focused checks and evidence; commit the bounded diff.
- [x] Obtain one independent read-only security review; no P0/P1 remains.

## STOP boundaries

No HG1-02 enrollment, reviewer action, scientific write, schema, frozen hash, HBA, credential, CAS, journal, or accepted M3 worktree change. Distinct-UID Runner socket testing is `NOT_RUN` when sudo cannot switch accounts noninteractively; unit policy checks do not count as that host test.
