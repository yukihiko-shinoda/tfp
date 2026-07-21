"""Render and run a project's Terraform commands, serialized across pytest-xdist workers."""

from __future__ import annotations

import asyncio
import fcntl
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from invoke import run
from invoke.exceptions import UnexpectedExit
from jinja2 import StrictUndefined
from jinja2 import Template

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from io import TextIOWrapper
    from typing import Any

    from invoke.runners import Promise
    from invoke.runners import Result

    from tfpcli.config import Project


class Error(Exception):
    """Base class for exceptions in this module.

    @see https://docs.python.org/3/tutorial/errors.html#user-defined-exceptions
    """


class FileLock:
    """Serialize access to a shared resource across pytest-xdist worker processes via an flock-based file."""

    ENCODING = "utf-8"
    FILE = Path("plan_logs") / "plan.lock"

    def __init__(self, text: str) -> None:
        self.text = text
        self.file: TextIOWrapper | None = None

    async def __aenter__(self) -> None:
        # Reason: This loop polls for release of an OS-level fcntl.flock() lock file created and removed
        # by other pytest-xdist worker processes (see tfpcli/cli.py's -n/--numprocesses), not by a coroutine
        # in this event loop. asyncio.Event only signals within a single process's event loop and cannot
        # observe another process's flock/file-existence state, so switching to it would silently break
        # cross-process locking:
        # - asyncio Synchronization Primitives
        #   https://docs.python.org/3/library/asyncio-sync.html
        # - Developing with asyncio
        #   https://docs.python.org/3/library/asyncio-dev.html
        while not await self.lock():  # noqa: ASYNC110
            await asyncio.sleep(0.25)

    async def lock(self) -> bool:
        if await self.is_locked():
            return False
        self.file = self.FILE.open("w", encoding=self.ENCODING)
        fcntl.flock(self.file, fcntl.LOCK_EX)
        await asyncio.sleep(0.25)
        return True

    async def __aexit__(self, *args: object) -> None:
        while await self.is_locked():
            if self.file:
                fcntl.flock(self.file, fcntl.LOCK_UN)
                self.file.close()
            self.file = None
            self.FILE.unlink()

    def __await__(self) -> Coroutine[Any, Any, None]:
        return self.__aenter__()

    async def is_locked(self) -> bool:
        for _ in range(3):
            if self.FILE.exists():
                return True
            await asyncio.sleep(0.25)
        return False


class Runner:
    """Render and run a single project's Terraform commands for one environment."""

    def __init__(self, project: Project, environment: dict[str, str]) -> None:
        # Ensures plan_logs/ exists before FileLock opens plan.lock below and before the caller
        # (tfpcli/tests/test_plan.py) writes this environment's log file.
        Path("plan_logs").mkdir(exist_ok=True)
        self.project_directory = self.render(project.directory, environment)
        self.command_select_environment = self.render(project.command_select_environment, environment)
        self.command_plan = self.render(project.command_plan, environment)
        self.lock_file = Path("plan_logs") / "plan.lock"

    async def execute(self) -> Result:
        """Install Terraform, select the environment, and run the plan.

        Environment selection is serialized with `FileLock` since `terraform workspace select` mutates state shared by
        concurrent pytest-xdist workers.
        """
        try:
            async with FileLock(self.command_select_environment):
                self.cd_and_run("tenv tf install")
                self.cd_and_run(self.command_select_environment)
                coroutine = self.cd_and_plan(self.command_plan)
                # Requires at least 1 seconds, otherwise, lock won't work well:
                # E           FileNotFoundError: [Errno 2] No such file or directory: 'plan_logs/plan.lock'
                # or
                # E       AssertionError: Error:
                # E         Error: HCP Terraform or Terraform Enterprise initialization required: please run "terraform init"
                # E
                # E         Reason: HCP Terraform configuration block has changed.
                # E
                # E         Changes to the HCP Terraform configuration block require reinitialization, to
                # E         discover any changes to the available workspaces.
                # E
                # E         To re-initialize, run:
                # E           terraform init
                # E
                # E         Terraform has not yet made changes to your existing configuration or state.
                await asyncio.sleep(1.5)
            promise = await coroutine
            return promise.join()
        except UnexpectedExit as error:
            return error.result

    def cd_and_run(self, command: str) -> Result:
        return run(f"cd {self.project_directory} && {command}", in_stream=False)

    async def cd_and_plan(self, command: str) -> Promise:
        # invoke.run() is typed to always return Result, but passing asynchronous=True makes it
        # actually return a Promise (a Result subclass) at runtime; see invoke.runners.Runner.run.
        return cast("Promise", run(f"cd {self.project_directory} && {command}", in_stream=False, asynchronous=True))

    def render(self, template: str, variable: dict[str, str]) -> str:
        # jinja2's Template.__new__() is intentionally typed to return Any ("it returns a Template,
        # but this breaks the sphinx build" per jinja2's own source), so .render() also resolves to
        # Any despite its own accurate `-> str` annotation.
        return cast("str", Template(template, undefined=StrictUndefined).render(**variable))
