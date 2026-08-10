"""
file_path_builder.py

Last edited: 2026-08-10
"""

import os
from hashlib import sha256
from pathlib import Path

from pytest_harness.constants_and_classes import (
    FilePaths,
    HASH_LENGTH,
    MAX_LOGDUO_STEM_LENGTH,
    WINDOWS_SAFE_PATH_LENGTH,
)

_IS_WINDOWS = os.name == "nt"


# --- _build_file_paths() ------------------------------------------------------
def _build_file_paths(
    *,
    relative_test_file_path: Path,
    test_file_dir: Path,
    output_dir_path: Path,
    coverage_temp_dir_path: Path,
) -> FilePaths:
    """
    Build filesystem-safe paths for one test file's generated artifacts.
    """

    log_stem, log_was_shortened = _build_safe_stem(
        relative_test_file_path,
        parent_dir_path=output_dir_path,
        filename_suffix=".log",
    )

    coverage_stem, _ = _build_safe_stem(
        relative_test_file_path,
        parent_dir_path=coverage_temp_dir_path,
        filename_prefix=".coverage.",
    )

    progress_stem, _ = _build_safe_stem(
        relative_test_file_path,
        parent_dir_path=coverage_temp_dir_path,
        filename_prefix="progress_",
        filename_suffix=".txt",
    )

    return FilePaths(
        test_file_path=test_file_dir / relative_test_file_path,
        test_file_log_path=output_dir_path / f"{log_stem}.log",
        coverage_data_file_path=(coverage_temp_dir_path / f".coverage.{coverage_stem}"),
        progress_file_path=coverage_temp_dir_path / f"progress_{progress_stem}.txt",
        test_file_log_name_was_shortened=log_was_shortened,
    )


# === Internal helpers =========================================================
def _build_safe_stem(
    file_path: Path,
    *,
    parent_dir_path: Path,
    filename_prefix: str = "",
    filename_suffix: str = "",
) -> tuple[str, bool]:

    safe_stem = "__".join(file_path.with_suffix("").parts)

    if _IS_WINDOWS:
        fixed_path = parent_dir_path / f"{filename_prefix}{filename_suffix}"
        max_length = min(MAX_LOGDUO_STEM_LENGTH, WINDOWS_SAFE_PATH_LENGTH - len(str(fixed_path)),)

    else:
        max_length = MAX_LOGDUO_STEM_LENGTH

    if len(safe_stem) <= max_length:
        return safe_stem, False
    stem_hash = sha256(safe_stem.encode("utf-8")).hexdigest()[:HASH_LENGTH]
    hash_suffix = f"__{stem_hash}"
    retained_length = max_length - len(hash_suffix)

    if retained_length <= 0:
        return stem_hash[:max_length], True

    return (
        f"{safe_stem[-retained_length:]}{hash_suffix}",
        True,
    )
