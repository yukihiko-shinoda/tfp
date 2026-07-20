# TFP

[![Test](https://github.com/yukihiko-shinoda/tfp/workflows/Test/badge.svg)](https://github.com/yukihiko-shinoda/tfp/actions?query=workflow%3ATest)
[![CodeQL](https://github.com/yukihiko-shinoda/tfp/workflows/CodeQL/badge.svg)](https://github.com/yukihiko-shinoda/tfp/actions?query=workflow%3ACodeQL)
[![Code Coverage](https://qlty.sh/gh/yukihiko-shinoda/projects/tfp/coverage.svg)](https://qlty.sh/gh/yukihiko-shinoda/projects/tfp)
[![Maintainability](https://qlty.sh/gh/yukihiko-shinoda/projects/tfp/maintainability.svg)](https://qlty.sh/gh/yukihiko-shinoda/projects/tfp)
[![Dependabot](https://flat.badgen.net/github/dependabot/yukihiko-shinoda/tfp?icon=dependabot)](https://github.com/yukihiko-shinoda/tfp/security/dependabot)
[![Python versions](https://img.shields.io/pypi/pyversions/tfp)](https://pypi.org/project/tfp/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/tfp)](https://pypi.org/project/tfp/)
[![X URL](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Fyukihiko-shinoda%2Ftfp)](https://x.com/intent/post?text=TFP&url=https%3A%2F%2Fpypi.org%2Fproject%2Ftfp%2F&hashtags=python)

Terraform parallel execution for each workspace.

## Advantage

* Terraform has no built-in way to run `plan` across multiple workspaces/environments at once — you either
  run each one by hand or script your own orchestration. TFP parallelizes them with `pytest-xdist`, so a
  project with N environments takes roughly as long as its slowest environment instead of the sum of all of
  them.
* `terraform workspace select` mutates state shared by every worker, so TFP serializes just that one step
  behind a cross-process file lock while still running the actual `plan` concurrently — real parallelism
  without workspace corruption.
* Terraform's plan-log wording has shifted across versions (0.13 / 0.14 / 0.15 / 1.0.6+). TFP's report
  generator recognizes all of them, so upgrading Terraform doesn't silently break your summaries.
* The bundled `tfp-report` command folds every environment's plan output into a single Markdown file —
  paste it into a PR description or CI job summary instead of linking to N separate logs.

## Quickstart

```console
pip install tfp
```

TFP assumes that Terraform is installed.
We recommend to use [tenv] (see [install-tenv.sh] for a reference install script).

Describe your project's environments in `tfp.yml` in your working directory:

```yaml
# You can define multiple terraform projects as dictionary.
# The key of dictionary is the value you pass to `tfp`, e.g. `tfp my-project`.
projects:
  my-project:
    # The directory to run `terraform plan` in.
    # This supports jinja to use a different directory per environment
    # (see the per-environment values example below).
    directory: infra
    # The command to select environment and prepare to plan.
    # This also supports jinja.
    command_select_environment: terraform workspace select {{ environment }}
    # The command to plan.
    # This also supports jinja.
    command_plan: terraform plan -detailed-exitcode -no-color
    # The dictionary of environments.
    # The key of each entry can be referenced from jinja (here, as `environment`).
    # You can add additional jinja parameters as the values of each entry.
    environments:
      dev: {}
      prod: {}
```

Then run:

```console
tfp my-project
```

Each environment's `terraform plan` output is written to `plan_logs/<environment>.log` (here,
`plan_logs/dev.log` and `plan_logs/prod.log`), and the command exits non-zero if any environment's plan
errors out.

<!-- markdownlint-disable no-trailing-punctuation -->
## How do I...
<!-- markdownlint-enable no-trailing-punctuation -->

### How do I control the number of parallel workers?

Pass `-n`/`--numprocesses`, forwarded to `pytest-xdist`'s `-n`. Defaults to `"auto"`, which
`tfp` resolves itself to `min(environment count, CPU count)` for the selected project — never
more workers than there are environments to plan:

```console
tfp my-project -n 4
```

### How do I use per-environment values inside my Terraform commands?

`directory`, `command_select_environment`, and `command_plan` are all rendered as Jinja templates with each
environment's dictionary as variables, so you can vary the working directory or commands per environment:

```yaml
projects:
  my-project:
    # directory, command_select_environment, and command_plan are all rendered as jinja
    # templates with each environment's dictionary as variables, so you can vary the
    # working directory or commands per environment.
    directory: my-project/environments/{{ environment_name }}
    command_select_environment: make reconfigure
    command_plan: make plan
    environments:
      dev:
        environment_name: development
      stg:
        environment_name: staging
      prod:
        environment_name: production
```

### How do I generate a single Markdown report from all environment plans?

```console
tfp-report
```

This reads every `*.log` file under `plan_logs/` and writes a combined `report.md`, one section per
environment.

## Credits

This package was created with [Cookiecutter] and the [yukihiko-shinoda/cookiecutter-pypackage] project template.

[Cookiecutter]: https://github.com/audreyr/cookiecutter
[yukihiko-shinoda/cookiecutter-pypackage]: https://github.com/yukihiko-shinoda/cookiecutter-pypackage
[tenv]: https://github.com/tofuutils/tenv
[install-tenv.sh]: install-tenv.sh
