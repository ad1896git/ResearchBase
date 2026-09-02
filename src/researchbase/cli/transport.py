"""Click transport normalization used by the Typer command tree."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import typer
from typer.core import TyperCommand, TyperGroup
from typer.core import _click as click

from researchbase.foundation.ids import new_uuid7

from .errors import CliTransportError
from .output import emit_error


def _request_id(ctx: click.Context, args: list[str]) -> UUID:
    raw = ctx.find_root().params.get("request_id")
    if not isinstance(raw, str):
        try:
            index = args.index("--request-id")
            raw = args[index + 1]
        except (ValueError, IndexError):
            raw = None
    try:
        return UUID(raw) if isinstance(raw, str) else new_uuid7()
    except ValueError:
        return new_uuid7()


def _normalize_click_error(
    ctx: click.Context, args: list[str], error: click.ClickException
) -> None:
    request_id = _request_id(ctx, args)
    transport_error = CliTransportError(
        "invalid CLI input",
        request_id=request_id,
        details={"reason": error.format_message()},
    )
    emit_error(transport_error, request_id, "--json" in args)


class StableTyperGroup(TyperGroup):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if "--json" in args:
            ctx.meta["json_requested"] = True
        try:
            return super().parse_args(ctx, args)
        except click.ClickException as error:
            _normalize_click_error(ctx, args, error)
            raise click.exceptions.Exit(2) from None


class StableTyperCommand(TyperCommand):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.ClickException as error:
            _normalize_click_error(ctx, args, error)
            raise click.exceptions.Exit(2) from None


def command_group(help_text: str) -> typer.Typer:
    return typer.Typer(cls=StableTyperGroup, help=help_text)


def add_command(
    group: typer.Typer, name: str, help_text: str, callback: Callable[..., object]
) -> None:
    group.command(name, cls=StableTyperCommand, help=help_text)(callback)
