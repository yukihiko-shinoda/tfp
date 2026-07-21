"""This module implements configuration."""

import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict

from dataclasses_json import DataClassJsonMixin
from yamldataclassconfig.config import YamlDataClassConfig


@dataclass
class Project(DataClassJsonMixin):
    """This class implements a project configuration section."""

    directory: str
    command_select_environment: str
    command_plan: str
    # Reason: `from __future__ import annotations` would stringify this annotation, but
    # dataclasses_json's schema builder reads `field.type` directly (not via
    # `typing.get_type_hints()`), so it would see the literal string "dict[str, str]" instead of a
    # real type, fail to recognize it as a container, and emit `UserWarning: Unknown type ...` at
    # schema-build time. Verified empirically: with the future import and PEP 585 `dict[...]`,
    # loading a real YAML config emitted that warning; with `typing.Dict` and no future import (the
    # current code), it loads cleanly under `-W error::UserWarning`. Confirmed still unfixed as of
    # dataclasses-json 0.6.7 (the version installed here) — the maintainer closed the report saying
    # there's no good fix without improvements to the `typing` API:
    # - Library is not compatible with "from __future__ import annotations" (PEP 563) · Issue #62
    #   https://github.com/lidatong/dataclasses-json/issues/62
    environments: Dict[str, Dict[str, str]]  # noqa: FA100

    def numprocesses_auto(self) -> int:
        """Return the worker count: one per environment, capped at the CPU count."""
        return min(len(self.environments), os.cpu_count() or 1)


@dataclass
class Config(YamlDataClassConfig):
    """This class implements configuration wrapping."""

    # Reason: same dataclasses_json/future-annotations incompatibility as `Project.environments`
    # above — `Config.projects` is introspected the same way to build its nested `Project` schema.
    projects: Dict[str, Project] = field(default_factory=dict)  # noqa: FA100
