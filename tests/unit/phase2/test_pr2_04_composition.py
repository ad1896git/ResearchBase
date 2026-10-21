from __future__ import annotations

from types import SimpleNamespace

import pytest

from researchbase.api import app as api_app
from researchbase.cli import composition as cli_composition


@pytest.mark.parametrize("module", [api_app, cli_composition])
def test_composition_registers_execution_service_with_scoped_uow(
    module, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        module,
        "load_settings",
        lambda: SimpleNamespace(
            log_level="WARNING",
            application_env="test",
            database_url="postgresql+psycopg://unused",
            artifact_store_root=tmp_path,
        ),
    )
    monkeypatch.setattr(module, "configure_logging", lambda *_args: None)
    monkeypatch.setattr(module, "create_database_engine", lambda _url: object())
    monkeypatch.setattr(module, "create_session_factory", lambda _engine: lambda: None)

    services = module.build_services()

    assert services.literature_search_executions is not None
    uow = services.literature_search_executions._uow_factory()
    assert uow._pr204_error_normalization is True
