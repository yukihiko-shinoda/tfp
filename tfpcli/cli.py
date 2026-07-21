"""Console script for tfp."""

from pathlib import Path

import click
import pytest

from tfpcli.config import Config


@click.command()
@click.argument("project")
@click.option(
    "-n",
    "--numprocesses",
    default="auto",
    help="Number of workers, forwarded to pytest-xdist's -n (default: min(environment count, CPU count)).",
)
def main(project: str, numprocesses: str) -> int:
    """Run `terraform plan` in parallel across every environment of PROJECT."""
    tests_directory = Path(__file__).resolve().parent / "tests"
    if numprocesses == "auto":
        config = Config()
        config.load(path="tfp.yml")
        numprocesses = str(config.projects[project].numprocesses_auto())
    return int(pytest.main([str(tests_directory), "--prj", project, "-n", numprocesses]))
