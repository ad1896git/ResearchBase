# Cross-Adapter Equivalence Report

The corrected cross-adapter acceptance captures real Application DTO outputs, HTTP JSON outputs, and CLI JSON
outputs. It compares the observational semantic projections and requires:

```text
Application == HTTP
Application == CLI
HTTP == CLI
```

Two independent fresh fixtures cover the adapter orders `CLI -> Application -> HTTP` and
`HTTP -> CLI -> Application`. The workflow uses the existing 35-route HTTP and 35-command CLI surfaces; neither
adapter calls the other. The combined E2E/architecture selection passed `66 passed`.
