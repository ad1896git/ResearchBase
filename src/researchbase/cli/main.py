"""Minimal Typer CLI smoke application."""

import typer

from researchbase import __version__

app = typer.Typer(help="ResearchBase bootstrap CLI.")


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@app.command()
def status() -> None:
    """Print the bootstrap CLI status."""
    typer.echo("ok")


if __name__ == "__main__":
    app()
