# HTTP and CLI Regression Report

The accepted HTTP and CLI contracts pass unchanged. The corrected architecture and regression selection verifies
the existing 35 HTTP routes and operation IDs, the existing 14 CLI groups and 35 commands, direct calls from both
adapters to Application, and zero CLI-to-HTTP loopback or HTTP-to-CLI dependency. Representative stable errors
remain equivalent across Application, HTTP, and CLI.

The full E2E and architecture selection passed `66 passed`.
