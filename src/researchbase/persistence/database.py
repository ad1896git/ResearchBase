"""Synchronous SQLAlchemy database adapter for the bootstrap smoke gate."""

from __future__ import annotations

import os
import threading
import types
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, engine_from_config, text
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from researchbase.foundation.bearing_binding import (
    absolute_path,
    check_cas,
    check_protected_parents,
    compare_database,
    load_binding_record,
)
from researchbase.foundation.bearing_binding_contracts import BindingError, BindingRecord
from researchbase.foundation.bearing_installation import (
    InstallationBindingWitness,
    VerifiedInstallation,
)
from researchbase.foundation.local_bearing_registration import LocalLease, acquire_lease
from researchbase.persistence.bearing_preflight import observe_database

DEFAULT_DATABASE_URL = "postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase"


class Base(DeclarativeBase):
    """Base for persistence-only SQLAlchemy models."""


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_database_engine(
    url: str | None = None, *, b04_write_timeouts: bool = False, b05_write_timeouts: bool = False
) -> Engine:
    """Opt B04 write factories into the guide's bounded first SHARE wait.

    Connection options apply before BEGIN; ordinary callers retain server defaults.
    B04 exact-read factories do not need this option.
    """
    options = (
        {"options": "-c lock_timeout=10000 -c statement_timeout=30000"}
        if b04_write_timeouts or b05_write_timeouts
        else {}
    )
    return create_engine(url or database_url(), future=True, connect_args=options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


def configure_revision_connection(connection) -> None:
    """Apply the B06 timeout profile before the driver's transaction begins.

    Session.connection() has a logical SQLAlchemy transaction, but psycopg has
    not sent BEGIN yet. Configure in autocommit, then restore on pool checkin;
    owning writers using the pool retain their original connection settings.
    """
    from sqlalchemy import event

    raw = connection.connection.driver_connection
    info = connection.info
    previous_autocommit = raw.autocommit
    raw.autocommit = True
    try:
        with raw.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            lock = cursor.fetchone()[0]
            cursor.execute("SHOW statement_timeout")
            statement = cursor.fetchone()[0]
            info["b06_timeouts"] = (lock, statement)
            pool = connection.engine.pool
            if not event.contains(pool, "checkin", _restore_revision_connection):
                event.listen(pool, "checkin", _restore_revision_connection)
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET statement_timeout = '30s'")
    except Exception:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION, "revision connection configuration failed"
        ) from None
    finally:
        raw.autocommit = previous_autocommit


def _restore_revision_connection(raw, record) -> None:
    bounds = record.info.pop("b06_timeouts", None)
    if raw is None or bounds is None:
        return
    autocommit = raw.autocommit
    try:
        raw.autocommit = True
        with raw.cursor() as cursor:
            cursor.execute("SELECT set_config('lock_timeout', %s, false)", (bounds[0],))
            cursor.execute("SELECT set_config('statement_timeout', %s, false)", (bounds[1],))
    except Exception:
        # A lost connection is discarded, never returned with leaked settings.
        record.invalidate()
    finally:
        if not raw.closed:
            raw.autocommit = autocommit


# Ordinary compatibility roots remain unregistered; only this module creates engines.
def create_search_result_engine(url: str) -> Engine:
    return create_engine(
        url,
        connect_args={
            "options": "-c lock_timeout=10s -c statement_timeout=30s",
            "connect_timeout": 10,
        },
    )


def create_migration_engine(configuration):
    return engine_from_config(configuration, prefix="sqlalchemy.", poolclass=NullPool)


def open_database_connection(engine: Engine):
    return engine.connect()


# Protected development roots. No Application/genuine consumer is wired to this path.


@dataclass
class _BindingState:
    record_path: Path
    record: BindingRecord
    stamp: tuple[int, ...]
    installation: InstallationBindingWitness
    lease: LocalLease
    engine: Engine
    connection: Connection
    driver: Any
    pid: int
    thread: threading.Thread
    factory_token: object
    connection_token: object
    creator: object
    creator_code: object
    function: types.FunctionType
    function_code: object
    methods: tuple[object, ...]
    observation: object | None = None
    session: Session | None = None
    invalid: bool = False
    closed: bool = False
    cleanup_unknown: bool = False
    cleanup_errors: tuple[Exception, ...] = ()


_bound_roots: dict[BoundBindingFactory, _BindingState] = {}
_observations: dict[BindingObservationProof, tuple[BoundBindingFactory, object]] = {}


def _method_codes():
    # Function object AND code identity: contextmanager wrappers share code but
    # have different captured generators. Neither may be substituted after issue.
    functions = (
        BoundBindingFactory.preflight,
        BoundBindingFactory.read_session,
        BoundBindingFactory.read_session.__wrapped__,
        BoundBindingFactory.close,
        BindingObservationProof._state,
        BindingObservationProof.assert_factory,
        BindingObservationProof.factory_identity.fget,
        BindingObservationProof.connection_identity.fget,
        BindingObservationProof.observation_id.fget,
        _identity,
        _recheck,
        observe_database,
        compare_database,
        load_binding_record,
        check_cas,
        check_protected_parents,
        InstallationBindingWitness.assert_identity,
        InstallationBindingWitness.assert_current,
    )
    identities: list[object] = [BoundBindingFactory, BindingObservationProof, Session]
    for function in functions:
        if not isinstance(function, types.FunctionType):
            raise BindingError("unsupported binding wrapper")
        identities.extend((function, function.__code__))
    return tuple(identities)


def _identity(factory):
    state = None
    try:
        state = _bound_roots[factory]
        if (
            state.closed
            or state.invalid
            or state.pid != os.getpid()
            or state.thread is not threading.current_thread()
            or datetime.now(UTC) >= state.record.expires_at
            or create_binding_preflight_factory is not state.creator
            or create_binding_preflight_factory.__code__ is not state.creator_code
            or state.function.__code__ is not state.function_code
            or any(a is not b for a, b in zip(_method_codes(), state.methods, strict=True))
            or state.connection.closed
            or state.connection.invalidated
            or state.driver.closed
            or state.driver.info.host != str(state.record.socket_directory)
            or state.driver.info.port != state.record.port
            or state.driver.info.dbname != state.record.database.name
            or state.driver.info.user != state.record.session_role.name
            or state.connection.connection.driver_connection is not state.driver
        ):
            raise BindingError("binding root identity lost")
        state.installation.assert_identity()
        return state
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        if (
            state is not None
            and state.pid == os.getpid()
            and state.thread is threading.current_thread()
        ):
            state.invalid = True
            state.observation = None
        raise BindingError("binding root unavailable") from exc


def _recheck(state):
    record, stamp = load_binding_record(state.record_path)
    if record != state.record or stamp != state.stamp:
        raise BindingError("binding record replaced")
    state.installation.assert_current()
    check_cas(record.cas)
    check_protected_parents(record.lease.path, record.lease.uid)
    state.lease.assert_binding(
        path=record.lease.path,
        device=record.lease.device,
        inode=record.lease.inode,
        uid=record.lease.uid,
        mode=record.lease.mode,
    )


class BindingObservationProof:
    """Issuer-owned non-I/O identity seam, never a write permit."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError("binding observations are issuer-owned")

    def __reduce_ex__(self, protocol):
        raise TypeError("binding observations cannot be serialized")

    def _state(self):
        try:
            factory, token = _observations[self]
            state = _identity(factory)
            if state.observation is not token or state.session is not None:
                raise BindingError("spent binding observation")
            return state
        except (KeyError, AttributeError) as exc:
            raise BindingError("invalid binding observation") from exc

    @property
    def factory_identity(self) -> object:
        return self._state().factory_token

    @property
    def connection_identity(self) -> object:
        return self._state().connection_token

    @property
    def observation_id(self) -> object:
        return self._state().observation

    def assert_factory(self, identity: object) -> None:
        state = self._state()
        if identity is not state.factory_token:
            raise BindingError("factory identity mismatch")


class BoundBindingFactory:
    """Private same-physical-connection development read factory; write adoption absent."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError("bound factories are issued only after preflight")

    def __reduce_ex__(self, protocol):
        raise TypeError("bound factories cannot be serialized")

    def preflight(self) -> BindingObservationProof:
        state = _identity(self)
        try:
            if (
                state.session is not None
                or state.connection.in_transaction()
                or state.driver.info.transaction_status != 0
            ):
                raise BindingError("binding connection is not idle")
            state.observation = None
            _recheck(state)
            with state.connection.begin():
                state.connection.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                actual = observe_database(state.connection)
                compare_database(state.record, actual)
            if state.connection.in_transaction() or state.driver.info.transaction_status != 0:
                raise BindingError("observation transaction did not end")
            _recheck(state)
            _identity(self)
            for old, (owner, _) in tuple(_observations.items()):
                if owner is self:
                    del _observations[old]
            token = object()
            state.observation = token
            proof = object.__new__(BindingObservationProof)
            _observations[proof] = (self, token)
            return proof
        except Exception as exc:
            state.invalid = True
            state.observation = None
            try:
                self.close()
            except Exception as cleanup:
                raise BindingError("binding preflight failed; cleanup unknown") from ExceptionGroup(
                    "preflight and cleanup failures", [exc, cleanup]
                )
            raise BindingError("binding preflight failed; root quarantined") from exc

    @contextmanager
    def read_session(self):
        """Restricted development reads only, retaining the same root pin afterwards."""
        self.preflight()
        state = _identity(self)
        session = Session(bind=state.connection, expire_on_commit=False, autoflush=False)
        state.session = session
        state.observation = None
        body_error = None
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            yield session
        except Exception as exc:
            body_error = exc
            state.invalid = True
        finally:
            errors = []
            for operation in (session.rollback, session.close):
                try:
                    operation()
                except Exception as exc:
                    errors.append(exc)
            state.session = None
            if not state.closed and (
                state.connection.in_transaction() or state.driver.info.transaction_status != 0
            ):
                errors.append(BindingError("read transaction cleanup unconfirmed"))
            state.cleanup_errors = tuple(errors)
            if body_error is None and not errors:
                try:
                    _identity(self)
                    _recheck(state)
                except Exception as exc:
                    errors.append(exc)
            if body_error is not None or errors:
                state.invalid = True
                failures = ([body_error] if body_error is not None else []) + errors
                try:
                    self.close()
                except Exception as cleanup:
                    failures.append(cleanup)
                raise BindingError("read root quarantined") from ExceptionGroup(
                    "read and cleanup failures", failures
                )

    def close(self) -> None:
        try:
            state = _bound_roots[self]
        except KeyError as exc:
            raise BindingError("invalid binding root") from exc
        if state.pid != os.getpid() or state.thread is not threading.current_thread():
            raise BindingError("only the original owner may clean this root")
        if state.closed:
            if state.cleanup_unknown:
                raise BindingError("binding cleanup outcome unknown")
            return
        state.closed = True
        state.observation = None
        for old, (owner, _) in tuple(_observations.items()):
            if owner is self:
                del _observations[old]
        errors = list(state.cleanup_errors)
        if state.session is not None:
            for operation in (state.session.rollback, state.session.close):
                try:
                    operation()
                except Exception as exc:
                    errors.append(exc)
            state.session = None
        for operation in (state.connection.rollback, state.connection.close, state.engine.dispose):
            try:
                operation()
            except Exception as exc:
                errors.append(exc)
        if not state.driver.closed:
            errors.append(BindingError("physical connection close unconfirmed"))
        # An unconfirmed database/session cleanup keeps the lease held. No new root
        # may overlap an unknown former pin merely because this object was invalidated.
        if not errors:
            try:
                state.lease.close_checked().assert_released_for(state.lease.identity_token)
            except Exception as exc:
                errors.append(exc)
        if errors:
            state.invalid = True
            state.cleanup_unknown = True
            raise BindingError("binding cleanup outcome unknown") from ExceptionGroup(
                "owned cleanup failures", errors
            )
        state.installation.close()


def create_binding_preflight_factory(
    *,
    binding_record_path: Path,
    installation: VerifiedInstallation,
    fixed_callable: types.FunctionType,
) -> BoundBindingFactory:
    """Protected startup only; no URL/caller observation/approval boolean accepted."""
    witness = lease = engine = connection = None
    connection_requested = False
    factory = None
    try:
        if any(key.startswith("PG") and value for key, value in os.environ.items()):
            raise BindingError("ambient PostgreSQL configuration denied")
        record, stamp = load_binding_record(binding_record_path)
        absolute_path(record.socket_directory)
        if "," in str(record.socket_directory) or not record.socket_directory.is_dir():
            raise BindingError("Unix socket host list denied")
        if datetime.now(UTC) < record.approved_at or datetime.now(UTC) >= record.expires_at:
            raise BindingError("binding approval outside validity window")
        if type(installation) is not VerifiedInstallation:
            raise BindingError("genuine installation verification required")
        witness = installation.consume_for_binding(
            expected=record.installation, fixed_callable=fixed_callable
        )
        check_cas(record.cas)
        check_protected_parents(record.lease.path, record.lease.uid)
        lease = acquire_lease(record.lease.path)
        lease.assert_binding(
            path=record.lease.path,
            device=record.lease.device,
            inode=record.lease.inode,
            uid=record.lease.uid,
            mode=record.lease.mode,
        )
        # Explicit parameters, no service/passfile/ambient TCP fallback. libpq receives no secrets.
        url = URL.create(
            "postgresql+psycopg",
            username=record.session_role.name,
            database=record.database.name,
            query={"host": str(record.socket_directory), "port": str(record.port)},
        )
        engine = create_engine(
            url,
            poolclass=NullPool,
            connect_args={
                "connect_timeout": 10,
                "passfile": "/dev/null",
                "options": (
                    "-c statement_timeout=10000 -c lock_timeout=3000 "
                    "-c default_transaction_read_only=on"
                ),
            },
        )
        connection_requested = True
        connection = engine.connect()
        driver = connection.connection.driver_connection
        factory = object.__new__(BoundBindingFactory)
        state = _BindingState(
            binding_record_path,
            record,
            stamp,
            witness,
            lease,
            engine,
            connection,
            driver,
            os.getpid(),
            threading.current_thread(),
            object(),
            object(),
            create_binding_preflight_factory,
            create_binding_preflight_factory.__code__,
            fixed_callable,
            fixed_callable.__code__,
            _method_codes(),
        )
        _bound_roots[factory] = state
        factory.preflight()
        return factory
    except Exception as exc:
        # Once a registered root exists its cleanup is the sole owner. Unknown
        # cleanup must not be retried/released through a second generic path.
        if factory is not None and factory in _bound_roots:
            state = _bound_roots[factory]
            if not state.closed:
                try:
                    factory.close()
                except Exception as cleanup:
                    raise BindingError("protected startup denied; cleanup unknown") from cleanup
            if state.cleanup_unknown:
                raise BindingError("protected startup denied; cleanup unknown") from exc
            raise BindingError("protected startup denied") from exc
        errors = []
        for resource, method in ((connection, "close"), (engine, "dispose")):
            if resource is not None:
                try:
                    getattr(resource, method)()
                except Exception as cleanup:
                    errors.append(cleanup)
        if connection_requested and (connection is None or not connection.closed):
            errors.append(BindingError("connection creation outcome unknown"))
        if not errors:
            for resource, method in ((lease, "close_checked"), (witness, "close")):
                if resource is not None:
                    try:
                        getattr(resource, method)()
                    except Exception as cleanup:
                        errors.append(cleanup)
                        break
        if errors:
            raise BindingError("protected startup denied; cleanup unknown") from errors[0]
        raise BindingError("protected startup denied") from exc
