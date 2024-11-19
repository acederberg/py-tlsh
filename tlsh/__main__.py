"""This will be entirely optional.

"""

import pathlib
import sys

import rich

from . import Tlsh

try:
    import typer
except ImportError:
    print("`typer` is required to have the `tlsh` command.")
    sys.exit(1)


cli = typer.Typer()


@cli.command()
def cli_hash(path: pathlib.Path):
    path = path.resolve()
    with open(path, "r") as file:
        data = file.read()

    rich.print("[green]" + Tlsh.compute_hash(data))


if __name__ == "__main__":
    cli()
