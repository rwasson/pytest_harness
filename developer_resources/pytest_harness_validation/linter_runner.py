"""
linter_runner.py

Run pytest_harness code-quality checks.
Use this script before committing meaningful source updates.

Checks:

- Ruff:
    Fixes import ordering in src, examples, and validation resources.
    Then checks src for lint issues such as unused imports, invalid syntax,
    unsafe patterns, overly complex functions, style violations, and other
    configured Ruff rules.

    For examples and validation resources, only import ordering is checked.

- Vulture:
    Checks src for likely dead or unreachable code.
    Uses --min-confidence 80 to reduce false positives.

- mypy:
    Checks whether type annotations and actual code usage agree.

This script applies only Ruff import-order fixes automatically.
All other findings require manual review.

Runs automatically in macOS, Ubuntu, and Windows when changes are pushed
to GitHub.

Called by:
    .github/workflows/tests.yml

Last edited: 2026-07-16
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from logduo import log

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CheckResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def _section(title: str) -> None:
    log("")
    log("=" * 87)
    log(title)
    log("=" * 87)


def _run_command(
    name: str,
    command: list[str],
) -> CheckResult:
    _section(f"Code quality check: {name}")

    log("Command:")
    log(" ".join(command))

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        log.exception(
            f"{name} crashed before completion."
        )

        return CheckResult(
            name=name,
            command=command,
            returncode=1,
            stdout="",
            stderr=repr(exc),
        )

    if completed.stdout.strip():
        log("STDOUT")
        log(completed.stdout)

    if completed.stderr.strip():
        log("STDERR")
        log(completed.stderr)

    if completed.returncode == 0:
        log.success(f"{name} passed.")
    else:
        log.error(
            f"{name} failed with return code "
            f"{completed.returncode}."
        )

    return CheckResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_linter_runners() -> list[CheckResult]:
    """Run all configured code-quality checks."""
    checks = [
        (
            "Ruff import order fix",
            [
                "ruff",
                "check",
                "src",
                "examples",
                "developer_resources/pytest_harness_validation",
                "--select",
                "I",
                "--fix",
            ],
        ),
        (
            "Ruff",
            [
                "ruff",
                "check",
                "src",
            ],
        ),
        (
            "Ruff import order",
            [
                "ruff",
                "check",
                "src",
                "examples",
                "developer_resources/pytest_harness_validation",
                "--select",
                "I",
            ],
        ),
        (
            "Vulture",
            [
                "vulture",
                "src",
                "--min-confidence",
                "80",
            ],
        ),
        (
            "mypy",
            [
                "mypy",
                "src/pytest_harness",
            ],
        ),
    ]

    return [
        _run_command(name, command)
        for name, command in checks
    ]


def failed_checks(
    results: list[CheckResult],
) -> list[CheckResult]:
    """Return checks that failed or crashed."""
    return [
        result
        for result in results
        if result.returncode != 0
    ]


def main() -> None:
    log.configure(
        log_dir_path=(
            PROJECT_ROOT
            / "developer_resources"
            / "pytest_harness_validation"
            / "logs"
        ),
        console_verbosity=3,
        log_verbosity=3,
    )

    results = run_linter_runners()
    failures = failed_checks(results)

    _section("Code quality summary")

    if not failures:
        log.success(
            "All code-quality checks passed."
        )
        log.close()
        return

    log.error(
        "Some code-quality checks failed:"
    )

    for failure in failures:
        log.error(
            f"- {failure.name}: "
            f"return code {failure.returncode}"
        )

    log.close()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
