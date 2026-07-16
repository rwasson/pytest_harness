"""
arg_resolver.py

Validate and normalize public pytest_harness arguments.

Last edited: 2026-07-16
"""

from __future__ import annotations

from pathlib import Path

from pytest_harness.constants_and_classes import (
    MAX_COVERAGE_WARNING_THRESHOLD,
    MIN_CONSOLE_WRAP_WIDTH,
    MIN_COVERAGE_WARNING_THRESHOLD,
    ValidatedHarnessArgs,
)


def _resolve_harness_args(
    *,
    test_dir: Path,
    log_dir: Path,
    source_dir: Path,
    include_list: list[str | Path] | None = None,
    exclude_list: list[str | Path] | None = None,
    coverage_warning_threshold: float | None,
    individual_logs: bool = True,
    show_source_file_coverage: bool = True,
    log_keep: int | None,
    console_wrap_width: int,
    show_skipped_and_xfailed: bool = False,
    debug_pytest_harness: bool = False,
) -> ValidatedHarnessArgs:
    """
    Validate and normalize arguments supplied to pytest_harness().
    """

    # Validate argument types before using Path methods.
    test_dir_path = _require_path(test_dir, name="test_dir").resolve()
    log_dir_path = _require_path(log_dir, name="log_dir").resolve()
    source_dir_path = _require_path(source_dir, name="source_dir").resolve()

    validated_include_list = _validate_selector_list(
        include_list,
        name="include_list",
    )
    validated_exclude_list = _validate_selector_list(
        exclude_list,
        name="exclude_list",
    )

    validated_coverage_warning_threshold = (
        _validate_coverage_warning_threshold(
            coverage_warning_threshold
        )
    )

    validated_individual_logs = _require_bool(
        individual_logs,
        name="individual_logs",
    )
    validated_show_source_file_coverage = _require_bool(
        show_source_file_coverage,
        name="show_source_file_coverage",
    )
    validated_show_skipped_and_xfailed = _require_bool(
        show_skipped_and_xfailed,
        name="show_skipped_and_xfailed",
    )
    validated_debug_pytest_harness = _require_bool(
        debug_pytest_harness,
        name="debug_pytest_harness",
    )

    validated_log_keep = _validate_log_keep(log_keep)
    validated_console_wrap_width = _validate_console_wrap_width(console_wrap_width)


    # Validate required input directories.
    _require_existing_directory(
        test_dir_path,
        name="Test directory",
    )
    _require_existing_directory(
        source_dir_path,
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
        test_dir=test_dir_path,
        log_dir=log_dir_path,
        source_dir=source_dir_path,
        include_list=validated_include_list,
        exclude_list=validated_exclude_list,
        coverage_warning_threshold=(
            validated_coverage_warning_threshold
        ),
        individual_logs=validated_individual_logs,
        show_source_file_coverage=(
            validated_show_source_file_coverage
        ),
        log_keep=validated_log_keep,
        console_wrap_width=validated_console_wrap_width,
        show_skipped_and_xfailed=validated_show_skipped_and_xfailed,
        debug_pytest_harness=validated_debug_pytest_harness,
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


def _validate_log_keep(
    value: int | None,
) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            "log_keep must be an int or None."
        )

    if value < 1:
        raise ValueError(
            "log_keep must be at least 1."
        )

    return value


def _validate_console_wrap_width(
    value: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("console_wrap_width must be an int.")

    if value < MIN_CONSOLE_WRAP_WIDTH:
        raise ValueError(f"console_wrap_width must be at least {MIN_CONSOLE_WRAP_WIDTH}.")

    return value
