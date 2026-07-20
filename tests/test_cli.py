"""Tests for `tfp.cli`."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from tfp import cli

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Note: docformatter 1.7.8 mangles a triple-quoted string passed directly as an argument to
# textwrap.dedent (even via the `text=` keyword), so it's dedented as a separate statement instead.
_CONFIG_YAML_RAW = """\
    projects:
      terraform-project-a:
        directory: terraform-project-a
        command_select_environment: terraform init && terraform workspace select default && terraform workspace show
        command_plan: terraform plan -detailed-exitcode -no-color
        environments:
          default: {}
    """
CONFIG_YAML = textwrap.dedent(_CONFIG_YAML_RAW)


class TestMain:
    """Tests for `tfp.cli.main`."""

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.main, ["--help"])
        assert result.exit_code == 0
        assert "--help" in result.output
        assert "Show this message and exit." in result.output

    def test_invokes_pytest_with_prj_and_numprocesses(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        """Default `-n auto` resolves to one worker, since the config defines one environment."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tfp.yml").write_text(CONFIG_YAML)
        mock_pytest_main = mocker.patch("pytest.main", return_value=0)
        runner = CliRunner()
        result = runner.invoke(cli.main, ["terraform-project-a"])
        assert result.exit_code == 0
        tests_directory = Path(cli.__file__).resolve().parent / "tests"
        mock_pytest_main.assert_called_once_with(
            [str(tests_directory), "--prj", "terraform-project-a", "-n", "1"],
        )

    def test_forwards_numprocesses_option(self, mocker: MockerFixture) -> None:
        mock_pytest_main = mocker.patch("pytest.main", return_value=0)
        runner = CliRunner()
        runner.invoke(cli.main, ["terraform-project-a", "-n", "4"])
        assert mock_pytest_main.call_args.args[0][-1] == "4"

    @pytest.mark.slow
    def test_returns_zero_when_terraform_plan_reports_no_changes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run the CLI end-to-end against a real Terraform project and expect a clean plan."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "terraform-project-a").mkdir()
        (tmp_path / "terraform-project-a" / "main.tf").touch()
        (tmp_path / "tfp.yml").write_text(CONFIG_YAML)
        runner = CliRunner()
        result = runner.invoke(cli.main, ["terraform-project-a", "-n", "0"], standalone_mode=False)
        assert result.return_value == 0
        log = (tmp_path / "plan_logs" / "default.log").read_text()
        assert "No changes. Your infrastructure matches the configuration." in log
