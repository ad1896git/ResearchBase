"""Existing HTTP and CLI surfaces expose one closed nested positive basis."""

import json
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from researchbase.api.app import create_app
from researchbase.cli.app import create_app as create_cli
from tests.integration.phase2.b19_basis_support import setup

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def wire(value):
    return json.loads(
        json.dumps(asdict(value), default=lambda x: str(x) if isinstance(x, UUID) else x)
    )


def test_real_v2_http_cli_parity(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    bundle = SimpleNamespace(
        application=object(),
        provenance=object(),
        governance=object(),
        governance_queries=object(),
        novelty=e["service"],
        verified_principal=e["author"],
    )
    app = create_app(cast(Any, bundle))

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.verified_principal = e["author"]
        return await call_next(request)

    body = wire(c)
    body.pop("project_id")
    path = f"/v1/projects/{e['project']}/novelty-assessments"
    cli = create_cli(cast(Any, bundle))
    with TestClient(app, raise_server_exceptions=False) as client:
        saved = client.post(path, json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["material_version"] == 2
        assert (
            client.get(path + "/" + str(c.id)).json()["content_hash"]
            == saved.json()["content_hash"]
        )
        result = CliRunner().invoke(
            cli,
            [
                "literature",
                "record-novelty-assessment",
                "--project-id",
                str(e["project"]),
                "--material-json",
                json.dumps(body),
                "--json",
            ],
        )
        assert result.exit_code == 0, (result.stdout, result.stderr, result.exception)
        assert saved.json()["content_hash"] in result.stdout
        for bad in (
            {**body, "material_version": 2},
            {**body, "prior_art_basis": [1]},
            {**body, "closeness_criteria": {"statements": [" "]}},
            {**body, "prior_art_basis": [{**body["prior_art_basis"][0], "hash": "x"}]},
        ):
            assert client.post(path, json=bad).status_code == 422
            result = CliRunner().invoke(
                cli,
                [
                    "literature",
                    "record-novelty-assessment",
                    "--project-id",
                    str(e["project"]),
                    "--material-json",
                    json.dumps(bad),
                    "--json",
                ],
            )
            assert result.exit_code == 2, (result.stdout, result.stderr, result.exception)


@pytest.mark.parametrize("failure", [ValueError, TypeError, RuntimeError])
def test_unexpected_v2_failures_stay_internal(novelty_env, monkeypatch, failure):
    e = novelty_env
    c, _, _, _ = setup(e)
    bundle = SimpleNamespace(
        application=object(),
        provenance=object(),
        governance=object(),
        governance_queries=object(),
        novelty=e["service"],
        verified_principal=e["author"],
    )
    app = create_app(cast(Any, bundle))

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.verified_principal = e["author"]
        return await call_next(request)

    def unexpected(*args):
        raise failure("secret-driver-details")

    monkeypatch.setattr(e["service"], "record_novelty_assessment", unexpected)
    body = wire(c)
    body.pop("project_id")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(f"/v1/projects/{e['project']}/novelty-assessments", json=body)
        assert response.status_code == 500 and "secret-driver-details" not in response.text
    result = CliRunner().invoke(
        create_cli(cast(Any, bundle)),
        [
            "literature",
            "record-novelty-assessment",
            "--project-id",
            str(e["project"]),
            "--material-json",
            json.dumps(body),
            "--json",
        ],
    )
    assert result.exit_code == 1 and "secret-driver-details" not in result.stderr
