"""Tests for `tfp.report`."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from tfp import report

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# Note: docformatter 1.7.8 mangles a triple-quoted string passed directly as an argument to
# textwrap.dedent (even via the `text=` keyword), so it's dedented as a separate statement instead.
_PLAN_LOG_NO_CHANGES_RAW = """\
    Initializing the backend...
    No changes. Your infrastructure matches the configuration.
    """
PLAN_LOG_NO_CHANGES = textwrap.dedent(_PLAN_LOG_NO_CHANGES_RAW)

_EXPECTED_REPORT_RAW = """\
    ## dev

    ```console
    No changes. Your infrastructure matches the configuration.

    ```

    ## prod

    ```console
    No changes. Your infrastructure matches the configuration.

    ```

    """
EXPECTED_REPORT = textwrap.dedent(_EXPECTED_REPORT_RAW)


class TestMain:
    """Tests for `tfp.report.main`."""

    def test_generates_report_from_plan_logs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Generate report.md from plan logs and verify its content."""
        monkeypatch.chdir(tmp_path)
        plan_logs = tmp_path / "plan_logs"
        plan_logs.mkdir()
        (plan_logs / "dev.log").write_text(PLAN_LOG_NO_CHANGES)
        (plan_logs / "prod.log").write_text(PLAN_LOG_NO_CHANGES)

        report.main()

        assert (tmp_path / "report.md").read_text() == EXPECTED_REPORT
