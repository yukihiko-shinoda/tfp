"""Render a Markdown report summarizing each environment's Terraform plan log."""

import re
from pathlib import Path

from jinja2 import Template

REGEX_NO_DIFF = r"No\schanges\.\sInfrastructure\sis\sup-to-date\."
REGEX_NO_DIFF_0_15_4 = r"No\schanges\.\sYour\sinfrastructure\smatches\sthe\sconfiguration\."
REGEX_EXISTS_DIFF = r"Terraform\sused\sthe\sselected\sproviders\sto\sgenerate\sthe\sfollowing\sexecution"
REGEX_EXISTS_DIFF_OUTPUT = r"Changes\sto\sOutputs\:"
REGEX_EXISTS_DIFF_0_13 = r"An\sexecution\splan\shas\sbeen\sgenerated\sand\sis\sshown\sbelow\."
REGEX_FAILED = r"Setup\sfailed:\sFailed\ssetting\sup\sTerraform binary:\sFailed\spushing\sbinary\sto\senvironment:\sexit\sstatus\s125"


class Splitter:
    """Extract the meaningful summary from a Terraform plan log, discarding boilerplate."""

    def __init__(self) -> None:
        # ---               : for Terraform 0.14 or less
        # ───               : for Terraform 0.15 ~ 1.0.5
        # "Terraform used ~": for Terraform 1.0.6 or more
        self.regex = re.compile(
            rf"({REGEX_NO_DIFF}|{REGEX_NO_DIFF_0_15_4}|{REGEX_EXISTS_DIFF}|{REGEX_EXISTS_DIFF_OUTPUT}|{REGEX_EXISTS_DIFF_0_13}|{REGEX_FAILED})\n",
        )

    def cut(self, path_to_file: Path) -> str:
        log = path_to_file.read_text(encoding="utf-8")
        list_log = self.regex.split(log)
        keyword = self.regex.search(log)
        if keyword is None:
            return list_log[-1].strip()
        return keyword[0] + list_log[-1].strip()


def main() -> None:
    """Render every plan log under `plan_logs/` into a single `report.md`."""
    log_files = Path("plan_logs").glob("*.log")
    generator = (Path(log_file) for log_file in log_files)
    splitter = Splitter()
    environments = {log_file.stem: splitter.cut(log_file) for log_file in generator}
    path_to_template = Path("report.md.jinja")
    if not path_to_template.exists():
        path_to_template = Path(__file__).resolve().parent / "report.md.jinja"
    template = Template(path_to_template.read_text(encoding="utf-8"), trim_blocks=True, lstrip_blocks=True)
    Path("report.md").write_text(template.render(environments=environments) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
