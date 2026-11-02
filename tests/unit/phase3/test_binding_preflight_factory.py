"""No supplied value or compatibility root can mint a development observation."""

import copy
import pickle
from pathlib import Path
from typing import Any, cast

import pytest

from researchbase.foundation.bearing_binding_contracts import BindingError
from researchbase.persistence import database as db


@pytest.mark.parametrize("cls", [db.BoundBindingFactory, db.BindingObservationProof])
def test_opaque_constructors(cls):
    with pytest.raises(TypeError):
        cls()
    fake = object.__new__(cls)
    for operation in (
        lambda: pickle.dumps(fake),
        lambda: copy.copy(fake),
        lambda: copy.deepcopy(fake),
    ):
        with pytest.raises(TypeError):
            operation()
    if cls is db.BindingObservationProof:
        with pytest.raises(BindingError):
            fake.assert_factory(object())
    else:
        with pytest.raises(BindingError):
            fake.preflight()


@pytest.mark.parametrize("name", ["PGHOSTADDR", "PGSERVICE", "PGPASSWORD", "PGPASSFILE"])
def test_ambient_pg_denied_before_open(monkeypatch, name):
    monkeypatch.setenv(name, "not-a-secret")
    monkeypatch.setattr(db, "create_engine", lambda *a, **k: pytest.fail("must not connect"))
    with pytest.raises(BindingError, match="protected startup denied"):
        db.create_binding_preflight_factory(
            binding_record_path=Path("/not-opened"),
            installation=cast(Any, object()),
            fixed_callable=lambda: None,
        )


def test_no_url_or_boolean_gate():
    with pytest.raises(TypeError):
        cast(Any, db.create_binding_preflight_factory)(url="ignored", verified=True)


def test_existing_search_factory_preserves_options(monkeypatch):
    result = object()
    seen = []
    monkeypatch.setattr(db, "create_engine", lambda *a, **k: seen.append((a, k)) or result)
    assert db.create_search_result_engine("postgresql://example") is result
    assert seen == [
        (
            ("postgresql://example",),
            {
                "connect_args": {
                    "options": "-c lock_timeout=10s -c statement_timeout=30s",
                    "connect_timeout": 10,
                }
            },
        )
    ]


def test_ordinary_factory_unregistered(monkeypatch):
    result = object()
    monkeypatch.setattr(db, "create_engine", lambda *a, **k: result)
    assert db.create_database_engine("ordinary") is result
    assert result not in db._bound_roots


def test_migration_delegation_preserves_nullpool(monkeypatch):
    from sqlalchemy.pool import NullPool

    seen = []
    result = object()

    def constructor(*args, **kwargs):
        seen.append((args, kwargs))
        return result

    monkeypatch.setattr(db, "engine_from_config", constructor)
    config = {"sqlalchemy.url": "ordinary-config"}
    assert db.create_migration_engine(config) is result
    assert seen == [((config,), {"prefix": "sqlalchemy.", "poolclass": NullPool})]


def test_connection_delegate_has_no_verification_mark():
    result = object()

    class Ordinary:
        def connect(self):
            return result

    assert db.open_database_connection(cast(Any, Ordinary())) is result
    assert result not in db._bound_roots
