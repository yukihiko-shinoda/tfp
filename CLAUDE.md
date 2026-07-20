# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

TFP ("Terraform parallel execution for each workspace") is a Python CLI (`tfp`, plus a companion
`tfp-report` command) that runs `terraform plan` across every environment/workspace of a project in
parallel, then folds the results into a single Markdown report. See [README.md](README.md) for the
end-user YAML config format (`tfp.yml`) and usage.

## Commands

```bash
# Setup
uv sync

# Testing
uv run invoke test              # Fast tests (excludes @pytest.mark.slow)
uv run invoke test.all          # All tests, including slow/end-to-end ones
uv run invoke test.coverage     # With coverage report
uv run pytest tests/test_cli.py::TestMain::test_forwards_numprocesses_option  # Single test

# Linting
uv run invoke lint              # Fast linters (xenon, ruff, bandit, dodgy, flake8, pydocstyle)
uv run invoke lint.deep         # Deep linters (mypy, pylint, semgrep)
uv run invoke lint.<tool>       # Individual tool, e.g. uv run invoke lint.mypy

# Formatting
uv run invoke style             # Format code
uv run invoke style --check     # Check without changes

uv run invoke --list            # Full task tree
```

`pyproject.toml`'s `[tool.pytest.ini_options] testpaths = ["tests"]` restricts default pytest/`invoke
test` collection to the top-level `tests/` directory — see Architecture below for why `tfp/tests/`
must *not* be collected this way.

## Architecture

### The core trick: pytest-xdist as the parallel execution engine

TFP doesn't hand-roll its own multiprocessing. `tfp/cli.py`'s `main()` shells out to `pytest.main()`,
pointed at the `tfp/tests/` directory bundled *inside the installed package* (not the top-level
`tests/` directory, which holds TFP's own unit tests):

```
tfp <project> -n 4
  -> pytest.main([<path to tfp/tests/>, "--prj", "<project>", "-n", "4"])
```

- [tfp/tests/conftest.py](tfp/tests/conftest.py) adds the `--prj` option and, via
  `pytest_generate_tests`, parametrizes every "test" over each environment defined for that project
  in `tfp.yml` (loaded through [tfp/config.py](tfp/config.py)'s `Config`/`Project` dataclasses).
- [tfp/tests/test_plan.py](tfp/tests/test_plan.py) has exactly one test function, `test()`. Each
  parametrized instance of it is really one environment's `terraform plan` run — pytest's identity as
  a test runner is being repurposed purely for its parallel-worker scheduling (`-n`) and
  parametrization machinery, not to check assertions about the codebase.
- [tfp/tests/testlibraries/runner.py](tfp/tests/testlibraries/runner.py)'s `Runner` renders each
  project's `directory` / `command_select_environment` / `command_plan` as Jinja2 templates (per
  environment) and executes them via `invoke.run()`.
- Because `terraform workspace select` mutates state shared across all pytest-xdist worker
  *processes*, `Runner.execute()` serializes just that one step behind `FileLock`, an `fcntl.flock()`
  wrapper keyed on `plan_logs/plan.lock`. The actual `plan` command still runs concurrently — this is
  what gives TFP real parallelism without workspace corruption. `FileLock` polls the lock file's
  existence rather than using `asyncio.Event`, since the synchronization is cross-process, not
  cross-coroutine (see the comment in `runner.py` for why an `asyncio` primitive would silently break
  this).
- `-n auto` (the CLI default) is resolved by `tfp` itself, not passed through to pytest-xdist
  verbatim: `Config.projects[project].numprocesses_auto()` in `tfp/config.py` computes
  `min(environment count, CPU count)`, so TFP never spawns more workers than there are environments to
  plan.

Each environment's plan output is written to `plan_logs/<environment>.log` by `test_plan.py::test`
itself (not by a pytest plugin/reporter), keyed off the `environment` fixture value injected by
`conftest.py`.

**Consequence for this codebase**: `tfp/tests/` looks like a test package but is production code —
changes there affect what `tfp` actually executes for users, not just CI. It's kept out of default
pytest collection (`testpaths = ["tests"]` in `pyproject.toml`) specifically so a plain `pytest` /
`invoke test` run doesn't try to execute it as a real test suite.

### Report generation

[tfp/report.py](tfp/report.py) (`tfp-report` entry point) is a separate concern from the plan
execution above: it globs `plan_logs/*.log` after a `tfp` run has populated them, uses `Splitter` to
strip Terraform's boilerplate preamble from each log (matching several regexes because plan-log
wording changed across Terraform 0.13 / 0.14 / 0.15 / 1.0.6+ — see the comments in `report.py` for
the exact version boundaries), and renders the trimmed summaries through a Jinja2 template
(`report.md.jinja`, checked for first in the CWD, else falling back to the one bundled next to
`report.py`) into `report.md`.

### Two-tests-directories layout

- `tests/` (top level) — TFP's own unit/integration tests for `tfp.cli`, `tfp.config`, `tfp.report`.
  Standard pytest, collected by default.
- `tfp/tests/` (inside the package) — shipped as part of the installed `tfp` package; this is the
  pytest suite that `tfp/cli.py` invokes at runtime against a *user's* Terraform project, described
  above. Excluded from default collection.

Keep this distinction in mind when adding tests: a bug fix to plan-execution behavior belongs under
`tfp/tests/`, while a bug fix to the CLI/config/report layer belongs under the top-level `tests/`.
