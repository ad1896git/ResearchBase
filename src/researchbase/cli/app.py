"""Typer CLI composition root for the Phase 1 Application boundary."""

from __future__ import annotations

import typer

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7

from .commands.agents import register as register_agents
from .commands.claim import register as register_claim
from .commands.evidence import register as register_evidence
from .commands.experiment import register as register_experiment
from .commands.governance import register as register_governance
from .commands.literature import register as register_literature
from .commands.literature_evidence import register as register_literature_evidence
from .commands.literature_search_execution import register as register_search_execution
from .commands.local import register as register_local
from .commands.metadata_observation import register as register_metadata
from .commands.research import register as register_research
from .commands.research_tasks import register as register_research_tasks
from .composition import build_services
from .context import CliServices, create_runtime
from .errors import CliTransportError
from .output import configure_command_logging, emit_error
from .transport import StableTyperGroup


def _local_actor_id(services: object) -> str | None:
    """Single-user local mode: the authenticated OS account is the owner."""

    identity = getattr(services, "local_identity", None)
    if identity is None:
        return None
    try:
        return str(identity.authenticate().actor_id)
    except ResearchBaseError:
        # Before `local init` / `local bootstrap`, commands that need an actor fail later.
        return None


def _root_callback(
    ctx: typer.Context,
    actor_id: str | None,
    request_id: str | None,
    correlation_id: str | None,
    causation_id: str | None,
    client_name: str | None,
    client_version: str | None,
    services: CliServices | None,
    verbose: bool = False,
) -> None:
    try:
        configure_command_logging(verbose)
        if services is None and actor_id is not None:
            raise ResearchBaseError(
                ErrorCode.FORBIDDEN,
                "不能用 --actor-id 指定身份。本地模式默认为当前系统用户（本人）。",
            )
        selected_services = services or build_services()
        if actor_id is None:
            actor_id = _local_actor_id(selected_services)
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
    register_metadata(app)
    register_literature_evidence(app)
    register_local(app)
    register_research(app)
    register_evidence(app)
    register_experiment(app)
    register_claim(app)
    register_governance(app)
    register_literature(app)
    register_search_execution(app)
    register_research_tasks(app)
    register_agents(app)

    @app.callback()
    def callback(
        ctx: typer.Context,
        actor_id: str | None = typer.Option(None, "--actor-id"),
        request_id: str | None = typer.Option(None, "--request-id"),
        correlation_id: str | None = typer.Option(None, "--correlation-id"),
        causation_id: str | None = typer.Option(None, "--causation-id"),
        client_name: str | None = typer.Option(None, "--client-name"),
        client_version: str | None = typer.Option(None, "--client-version"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细日志（默认隐藏）。"),
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
            verbose,
        )

    return app


app = create_app()
