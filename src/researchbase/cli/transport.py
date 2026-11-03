"""Click transport normalization used by the Typer command tree."""

from __future__ import annotations

import re
from collections.abc import Callable
from uuid import UUID

import typer
from typer._click.exceptions import UsageError
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


_USAGE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"No such option: (\S+)"), "没有这个参数：{0}"),
    (re.compile(r"No such command '([^']+)'"), "没有这个命令：{0}"),
    (re.compile(r"Missing option '([^']+)'"), "缺少必填参数：{0}"),
    (re.compile(r"Missing argument '([^']+)'"), "缺少必填位置参数：{0}"),
    (re.compile(r"Option '([^']+)' requires an argument"), "参数 {0} 需要一个值"),
    (re.compile(r"Got unexpected extra argument \(([^)]*)\)"), "多余的参数：{0}"),
)


def _chinese_usage(message: str) -> str:
    """Plain Chinese reason for a Click usage error; the English original is kept as a fallback."""

    for pattern, template in _USAGE_PATTERNS:
        match = pattern.search(message)
        if match:
            return template.format(*match.groups()) + "。可运行 --help 查看用法"
    return message


def _normalize_click_error(
    ctx: click.Context, args: list[str], error: click.ClickException
) -> None:
    request_id = _request_id(ctx, args)
    transport_error = CliTransportError(
        "invalid CLI input",
        request_id=request_id,
        details={"reason": _chinese_usage(error.format_message())},
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

    def invoke(self, ctx: click.Context) -> object:
        # Unknown subcommands are resolved here, after parse_args.
        try:
            return super().invoke(ctx)
        except UsageError as error:
            _normalize_click_error(ctx, [], error)
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
