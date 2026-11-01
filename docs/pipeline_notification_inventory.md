# Durable notification inventory

This bounded E04 maintenance packet adds a read-only diagnostic for the existing
wakeup `state/notifications` directory. It verifies content-addressed event bytes
and lists every event with counts by recorded status. It does not send messages,
alter scheduling, resolve ledger state, or change existing notification producers.
Parent E04 remains open; this packet is medium risk under its frozen maintenance
scope and requires independent review, seven exact-head CI checks and owner label.

Run with the project's absolute venv interpreter from this checkout:

```sh
/absolute/project/.venv/bin/python3 -m scripts.pipeline_notifications \
  --directory /absolute/timer/state/notifications
```

The JSON is explicitly historical: an old `blocked` event remains present after a
task completes. `live_task_state_verified` is always false. Use the task's validated
ledger and any owner reconciliation receipt to determine its current status.
No event is treated as proof of a successful merge or a new authorization.

Missing/noncanonical directories, unexpected entries, symlinks, corrupt JSON,
digest mismatches, missing status, over 10,000 entries, events over 64 KiB, and
concurrent event arrivals fail explicitly with exit 2 and a diagnostic on stderr;
there is no partial success output. A stable empty directory is valid. The tool
does not create even a missing notification directory or write report files.

Acceptance requires malformed-event and history-preservation tests, existing
pipeline regression, static checks, and a read-only smoke against copied real
event bytes. Rollback is removing use of this optional diagnostic; no runtime
deployment or new timer is included.
