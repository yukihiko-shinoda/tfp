"""Run `terraform plan` for every environment of the project selected via `--prj`."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from tfpcli.tests.testlibraries.runner import Runner

if TYPE_CHECKING:
    from tfpcli.config import Project


def test(project: Project, environment: dict[str, str]) -> None:
    exit_code_diff_present = 2
    runner = Runner(project, environment)
    result = asyncio.run(runner.execute())
    (Path("plan_logs") / f"{environment['environment']}.log").write_text(result.stdout, encoding="utf-8")
    assert result.exited == 0 or (
        result.exited == exit_code_diff_present
        and isinstance(result.stdout, str)
        and "Plan: 0 to add, 0 to change, 0 to destroy." in result.stdout
    ), (
        "Succeeded with non-empty diff (changes present)"
        if result.exited == exit_code_diff_present
        else f"Error: {result.stderr}"
    )
