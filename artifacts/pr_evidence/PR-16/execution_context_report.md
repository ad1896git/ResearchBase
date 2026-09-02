# ExecutionContext Report

The shared root options map exactly as follows:

| CLI option | ExecutionContext field |
|---|---|
| `--actor-id` | `actor_id` |
| `--request-id` | `request_id` |
| `--correlation-id` | `correlation_id` |
| `--causation-id` | `causation_id` |
| fixed | `client_type = "cli"` |
| `--client-name` | `client_name` |
| `--client-version` | `client_version` |

Default client name is `researchbase-cli`; default version is the package version. Actor context is required
only where the accepted Application command requires it. Query commands do not invent an actor.

The unit contract test asserts exact actor/request/correlation/causation/client forwarding. Supplied IDs are
preserved as UUID values, absent request IDs are generated once, and invocation state is not shared between
successive calls.
