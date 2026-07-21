"""Parametrize integration tests from the project selected via the `--prj` option."""

import pytest

from tfpcli.config import Config

CONFIG = Config()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--prj", help="select project")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "environment" in metafunc.fixturenames:
        project_name = metafunc.config.getoption("prj")
        CONFIG.load(path="tfp.yml")
        project = CONFIG.projects[project_name]
        metafunc.parametrize("project", [project])
        metafunc.parametrize(
            "environment",
            [dict(value, environment=key) for key, value in project.environments.items()],
        )
