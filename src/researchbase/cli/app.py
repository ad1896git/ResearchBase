"""Typer CLI composition root for the Phase 1 Application boundary."""

from __future__ import annotations

import typer

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7

from .commands.claim import register as register_claim
from .commands.evidence import register as register_evidence
from .commands.experiment import register as register_experiment
from .commands.governance import register as register_governance
from .commands.literature import register as register_literature
from .commands.literature_search_execution import register as register_search_execution
from .commands.local import register as register_local
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
    try:
        if services is None and (
            actor_id is not None or ctx.invoked_subcommand not in {None, "local", "literature"}
        ):
            raise ResearchBaseError(
                ErrorCode.FORBIDDEN,
                "use authenticated local or literature commands; actor overrides are forbidden",
            )
        selected_services = services or build_services()
        ctx.obj = create_runtime(
            selected_services,
            actor_id,
            request_id,
            correlation_id,
            causation_id,
            client_name,
            client_version,
        )
    except ResearchBaseError as exc:
        emit_error(exc, new_uuid7(), bool(ctx.meta.get("json_requested")))
        raise typer.Exit(code=3) from None
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
    register_local(app)
    register_research(app)
    register_evidence(app)
    register_experiment(app)
    register_claim(app)
    register_governance(app)
    register_literature(app)
    register_search_execution(app)

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
