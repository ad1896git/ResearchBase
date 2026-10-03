"""Typer CLI composition root for the Phase 1 Application boundary."""

from __future__ import annotations

import typer

from .commands.claim import register as register_claim
from .commands.evidence import register as register_evidence
from .commands.experiment import register as register_experiment
from .commands.governance import register as register_governance
from .commands.literature import register as register_literature
from .commands.research import register as register_research
from .composition import build_services
from .context import CliServices, create_runtime
from .errors import CliTransportError
from .output import emit_error
from .transport import StableTyperGroup


def _root_callback(
    ctx: typer.Context,
    actor_id: str | None,
    request_id: str | None,
    correlation_id: str | None,
    causation_id: str | None,
    client_name: str | None,
    client_version: str | None,
    services: CliServices | None,
) -> None:
    selected_services = services or build_services()
    try:
        ctx.obj = create_runtime(
            selected_services,
            actor_id,
            request_id,
            correlation_id,
            causation_id,
            client_name,
            client_version,
        )
    except CliTransportError as exc:
        emit_error(exc, exc.request_id, bool(ctx.meta.get("json_requested")))
        raise typer.Exit(code=2) from None
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def create_app(services: CliServices | None = None) -> typer.Typer:
    app = typer.Typer(
        cls=StableTyperGroup,
        name="researchbase",
        help="ResearchBase Phase 1 CLI.",
        invoke_without_command=True,
        no_args_is_help=False,
    )
    register_research(app)
    register_evidence(app)
    register_experiment(app)
    register_claim(app)
    register_governance(app)
    register_literature(app)

    @app.callback()
    def callback(
        ctx: typer.Context,
        actor_id: str | None = typer.Option(None, "--actor-id"),
        request_id: str | None = typer.Option(None, "--request-id"),
        correlation_id: str | None = typer.Option(None, "--correlation-id"),
        causation_id: str | None = typer.Option(None, "--causation-id"),
        client_name: str | None = typer.Option(None, "--client-name"),
        client_version: str | None = typer.Option(None, "--client-version"),
    ) -> None:
        _root_callback(
            ctx,
            actor_id,
            request_id,
            correlation_id,
            causation_id,
            client_name,
            client_version,
            services,
        )

    return app


app = create_app()
