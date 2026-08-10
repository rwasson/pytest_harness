"""
arg_resolver.py

Validate and normalize public pytest_harness arguments.

Last edited: 2026-08-10
"""

from __future__ import annotations

from pathlib import Path
from secrets import randbelow

from rich.console import Console
from rich.text import Text

from pytest_harness.constants_and_classes import (
    MAX_COVERAGE_WARNING_THRESHOLD,
    MIN_COVERAGE_WARNING_THRESHOLD,
    MIN_WRAP_WIDTH,
    ValidatedHarnessArgs,
)

_MAX_RANDOM_ORDER_SEED = 2_147_483_647


def _resolve_harness_args(  # noqa PLR0913   # more than 15 args appropriate
    *,
    test_file_dir: Path,
    log_dir: Path,
    tested_code_dir: Path,
    include_list: list[str | Path] | None = None,
    exclude_list: list[str | Path] | None = None,
    random_order: bool = False,
    random_order_seed: int | None = None,
    test_function_timeout: int | float | None = None,
    runner_log: bool = True,
    test_file_logs: bool = True,
    log_keep: int | None,
    console_dashboard: bool = False,
    console_theme: str = "dark",
    dashboard_width: int,
    show_source_file_coverage: bool = True,
    show_skipped_and_xfailed: bool = False,
    coverage_warning_threshold: float | None,
    debug_harness: bool = False,
) -> ValidatedHarnessArgs:
    """
    Validate and normalize arguments supplied to pytest_harness().
    """

    # Validate argument types before using Path methods.
    test_file_dir_path = _require_path(test_file_dir, name="test_file_dir").resolve()
    log_dir_path = _require_path(log_dir, name="log_dir").resolve()
    tested_code_dir_path = _require_path(tested_code_dir, name="tested_code_dir").resolve()

    validated_include_list = _validate_selector_list(
        include_list,
        name="include_list",
    )
    validated_exclude_list = _validate_selector_list(
        exclude_list,
        name="exclude_list",
    )

    validated_random_order = _require_bool(
        random_order,
        name="random_order",
    )
    resolved_random_order_seed = _resolve_random_order_seed(
        random_order=validated_random_order,
        random_order_seed=random_order_seed,
    )
    validated_test_function_timeout = _validate_test_function_timeout(
        test_function_timeout
    )

    validated_runner_log = _require_bool(
        runner_log,
        name="runner_log",
    )
    validated_test_file_logs = _require_bool(
        test_file_logs,
        name="test_file_logs",
    )
    validated_log_keep = _validate_log_keep(log_keep)

    validated_console_dashboard = _require_bool(
        console_dashboard,
        name="console_dashboard",
    )
    validated_console_theme = _validate_console_theme(console_theme)
    validated_dashboard_width = _validate_dashboard_width(dashboard_width)
    validated_show_source_file_coverage = _require_bool(
        show_source_file_coverage,
        name="show_source_file_coverage",
    )
    validated_show_skipped_and_xfailed = _require_bool(
        show_skipped_and_xfailed,
        name="show_skipped_and_xfailed",
    )
    validated_coverage_warning_threshold = (
        _validate_coverage_warning_threshold(
            coverage_warning_threshold
        )
    )

    validated_debug_harness = _require_bool(
        debug_harness,
        name="debug_harness",
    )

    # Validate required input directories.
    _require_existing_directory(
        test_file_dir_path,
        name="Test directory",
    )
    _require_existing_directory(
        tested_code_dir_path,
        name="Source directory",
    )

    # Validate output path before creating it.
    if log_dir_path.exists() and not log_dir_path.is_dir():
        raise RuntimeError(
            "Log directory path exists but is not a directory:\n"
            f"    {log_dir_path}"
        )

    # Perform filesystem mutation only after every argument has passed.
    if not log_dir_path.exists():
        try:
            log_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                "Unable to create log directory:\n"
                f"    {log_dir_path}\n"
                f"    {exc}"
            ) from exc

        print(
            "Creating log directory:\n"
            f"    {log_dir_path}"
        )

    return ValidatedHarnessArgs(
        test_file_dir=test_file_dir_path,
        log_dir=log_dir_path,
        tested_code_dir=tested_code_dir_path,
        include_list=validated_include_list,
        exclude_list=validated_exclude_list,
        random_order=validated_random_order,
        random_order_seed=resolved_random_order_seed,
        test_function_timeout=validated_test_function_timeout,
        runner_log=validated_runner_log,
        test_file_logs=validated_test_file_logs,
        log_keep=validated_log_keep,
        console_dashboard=validated_console_dashboard,
        console_theme=validated_console_theme,
        dashboard_width=validated_dashboard_width,
        show_source_file_coverage=validated_show_source_file_coverage,
        show_skipped_and_xfailed=validated_show_skipped_and_xfailed,
        coverage_warning_threshold=validated_coverage_warning_threshold,
        debug_harness=validated_debug_harness,
    )


# === Internal helpers ========================================================

def _require_path(
    value: object,
    *,
    name: str,
) -> Path:
    if not isinstance(value, Path):
        raise TypeError(
            f"{name} must be a pathlib.Path instance.\n"
            f"Received: {type(value).__name__}"
        )

    return value


def _require_existing_directory(
    path: Path,
    *,
    name: str,
) -> None:
    if not path.exists():
        raise RuntimeError(
            f"{name} does not exist:\n"
            f"    {path}"
        )

    if not path.is_dir():
        raise RuntimeError(
            f"{name} path is not a directory:\n"
            f"    {path}"
        )

    try:
        next(path.iterdir(), None)
    except OSError as exc:
        raise RuntimeError(
            f"{name} cannot be read:\n"
            f"    {path}\n"
            f"    {exc}"
        ) from exc


def _validate_selector_list(
    value: list[str | Path] | None,
    *,
    name: str,
) -> list[str | Path] | None:
    if value is None:
        return None

    if not isinstance(value, list):
        raise TypeError(
            f"{name} must be a list of str or Path values, or None."
        )

    if not value:
        raise ValueError(
            f"{name} cannot be empty.\n"
            "Use None when no selectors are needed."
        )

    validated: list[str | Path] = []

    for index, entry in enumerate(value):
        if not isinstance(entry, (str, Path)):
            raise TypeError(
                f"{name}[{index}] must be str or Path.\n"
                f"Received: {type(entry).__name__}"
            )

        if isinstance(entry, str):
            if not entry.strip():
                raise ValueError(
                    f"{name}[{index}] cannot be an empty string."
                )

            validated.append(entry.strip())
        else:
            validated.append(entry)

    return validated


def _require_bool(
    value: object,
    *,
    name: str,
) -> bool:
    if type(value) is not bool:
        raise TypeError(
            f"{name} must be bool.\n"
            f"Received: {type(value).__name__}"
        )

    return bool(value)


def _resolve_random_order_seed(
    *,
    random_order: bool,
    random_order_seed: int | None,
) -> int | None:
    if not random_order:
        return None

    if random_order_seed is None:
        return randbelow(_MAX_RANDOM_ORDER_SEED) + 1

    if isinstance(random_order_seed, bool) or not isinstance(random_order_seed, int):
        raise TypeError(
            "random_order_seed must be an int or None."
        )

    if random_order_seed < 1:
        raise ValueError(
            "random_order_seed must be at least 1."
        )

    return random_order_seed


def _validate_test_function_timeout(
    value: int | float | None,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("test_function_timeout must be an int, float, or None.")

    if value <= 0:
        raise ValueError("test_function_timeout must be greater than 0 seconds.")

    return float(value)


def _validate_log_keep(
    value: int | None,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("log_keep must be an int or None.")

    if value < 1:
        raise ValueError("log_keep must be at least 1.")

    return value


def _validate_console_theme(
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            'console_theme must be "dark" or "light".'
        )

    normalized_value = value.strip().lower()

    if normalized_value not in {"dark", "light"}:
        preconfig_console = Console(force_terminal=True)

        warning_text = Text()
        warning_text.append(
            "WARNING:",
            style="bold yellow",
        )
        warning_text.append(
            ' console_theme must be either "dark" or "light" '
            '(default="dark").'
        )

        preconfig_console.print(warning_text)
        normalized_value = "dark"

    return normalized_value


def _validate_dashboard_width(
    value: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("dashboard_width must be an int.")

    if value < MIN_WRAP_WIDTH:
        raise ValueError(f"dashboard_width must be at least {MIN_WRAP_WIDTH}.")

    return value


def _validate_coverage_warning_threshold(
    value: float | int | None,
) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            "coverage_warning_threshold must be a number or None."
        )

    normalized_value = float(value)

    if not MIN_COVERAGE_WARNING_THRESHOLD <= normalized_value <= MAX_COVERAGE_WARNING_THRESHOLD:
        raise ValueError(
            f"coverage_warning_threshold must be between "
            f"{MIN_COVERAGE_WARNING_THRESHOLD} and {MAX_COVERAGE_WARNING_THRESHOLD}."
        )

    return normalized_value
