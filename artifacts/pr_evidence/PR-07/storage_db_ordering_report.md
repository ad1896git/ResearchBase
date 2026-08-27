# Storage/DB ordering report

The registration path is:

```text
put_verified -> verify -> open/size validation -> one DB transaction -> commit
```

The ordering integration test records the store event before the
`INSERT INTO artifact_versions` event. An injected DB failure rolls back the database row
while leaving verified content-addressed bytes available, as explicitly allowed by PR-07.
No distributed transaction or garbage collector was added.
