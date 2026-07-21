"""Tests for `tfpcli.config`."""

import os

from tfpcli.config import Project


class TestProject:
    """Tests for `tfpcli.config.Project`."""

    def test_numprocesses_auto(self) -> None:
        """One worker per environment when there are fewer environments than CPUs."""
        project = Project(
            directory="terraform-project-a",
            command_select_environment="",
            command_plan="",
            environments={"default": {}},
        )
        assert project.numprocesses_auto() == 1

    def test_numprocesses_auto_caps_at_cpu_count(self) -> None:
        """Worker count never exceeds the CPU count, even with more environments."""
        cpu_count = os.cpu_count() or 1
        project = Project(
            directory="terraform-project-a",
            command_select_environment="",
            command_plan="",
            environments={f"env-{index}": {} for index in range(cpu_count + 10)},
        )
        assert project.numprocesses_auto() == cpu_count
