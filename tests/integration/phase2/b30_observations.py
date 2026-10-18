"""Bounded SQL observations, including server settings and transaction boundaries."""

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import monotonic, sleep

from sqlalchemy import event, text


@dataclass
class ObservedTransaction:
    backend_pid: int
    statements: list = field(default_factory=list)
    parameters: list = field(default_factory=list)


class SQLObservations(list):
    def __init__(self):
        super().__init__()
        self.transactions = []


@contextmanager
def sql_protocol(engine):
    observed = SQLObservations()
    active = {}

    def begin(conn):
        dbapi = conn.connection.driver_connection
        transaction = ObservedTransaction(dbapi.info.backend_pid)
        active[dbapi] = transaction
        observed.transactions.append(transaction)

    def end(conn):
        active.pop(conn.connection.driver_connection, None)

    def observe(conn, cursor, sql, parameters, context, executemany):
        dbapi = cursor.connection
        # SHOW observes the actual server transaction, including SQL SET TRANSACTION;
        # psycopg's connection defaults need not reflect that SQL. Use a separate
        # raw cursor so the application cursor's result is preserved. These probes
        # run AFTER the owner's statement and cannot precede its first SHARE.
        with dbapi.cursor() as probe:
            probe.execute("SHOW transaction_isolation")
            isolation = probe.fetchone()[0].upper().replace(" ", "_")
            probe.execute("SHOW transaction_read_only")
            readonly = probe.fetchone()[0] == "on"
        entry = (sql, isolation, readonly)
        observed.append(entry)
        active[dbapi].statements.append(entry)
        active[dbapi].parameters.append(parameters)

    for name, callback in (("begin", begin), ("commit", end), ("rollback", end)):
        event.listen(engine, name, callback)
    event.listen(engine, "after_cursor_execute", observe)
    try:
        yield observed
    finally:
        event.remove(engine, "after_cursor_execute", observe)
        for name, callback in (("begin", begin), ("commit", end), ("rollback", end)):
            event.remove(engine, name, callback)


def assert_snapshot_read(statements, *, snapshots=None):
    assert statements
    if snapshots is not None:
        assert len(statements.transactions) == snapshots
    assert all(isolation == "REPEATABLE_READ" and readonly for _, isolation, readonly in statements)
    for sql, _, _ in statements:
        normalized = " ".join(sql.upper().split())
        assert normalized.startswith(("SELECT ", "WITH ", "SHOW ", "SET TRANSACTION ")), sql
        assert not re.search(
            r"\b(?:FOR\s+(?:(?:NO\s+)?KEY\s+)?(?:UPDATE|SHARE)|"
            r"(?:INSERT|UPDATE|DELETE|MERGE|CALL|DO|COPY|LOCK)\b|"
            r"[\w.]*ADVISORY[\w]*\s*\(|[\w.]*SET_CONFIG\s*\(|"
            r"[\w.]*RB_PHASE2_LOCK_[\w]*\s*\(|[\w.]*NEXTVAL\s*\(|"
            r"[\w.]*SETVAL\s*\(|[\w.]*PG_(?:NOTIFY|TERMINATE_BACKEND)\s*\()",
            normalized,
        ), sql


def assert_first_share(statements, inventory, isolation="READ_COMMITTED"):
    groups = getattr(statements, "transactions", None)
    groups = [t.statements for t in groups] if groups is not None else [statements]
    writers = 0
    for group in groups:
        if not group:
            continue
        if all(readonly for _, _, readonly in group):
            assert_snapshot_read(group)
            continue
        writers += 1
        assert group[0] == (inventory, isolation, False), group[:3]
        assert all(mode == isolation and not readonly for _, mode, readonly in group)
    assert writers


def poll_db_clock(connection, boundary, *, timeout=15):
    deadline = monotonic() + timeout
    while True:
        at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at > boundary:
            return at
        assert monotonic() < deadline, "database clock did not reach boundary within deadline"
        sleep(0.02)
