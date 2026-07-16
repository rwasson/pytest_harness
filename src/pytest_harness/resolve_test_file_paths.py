"""
resolve_test_file_paths.py

Last edited: 2026-07-15
"""

from pathlib import Path


# --- _resolve_test_file_paths() -----------------------------------------------
def _resolve_test_file_paths(
    *,
    test_dir_path: Path,
    include_list: list[str | Path] | None,
    exclude_list: list[str | Path] | None,
) -> list[Path]:
    """
    Return selected pytest test-file paths relative to test_dir_path.
    Selection supports:
    - recursive discovery of test_*.py
    - optional include_list
    - optional exclude_list
    - file or directory selectors, with or without .py

    Detailed selector rules are documented in README.md.
    """

    test_dir_path = test_dir_path.resolve()

    if not test_dir_path.exists():
        raise RuntimeError(
            "Test directory does not exist:\n"
            f"    {test_dir_path}"
        )

    if not test_dir_path.is_dir():
        raise RuntimeError(
            "Test directory path is not a directory:\n"
            f"    {test_dir_path}"
        )

    def make_absolute(entrypath: str | Path) -> Path:
        entry_path = Path(entrypath)

        if entry_path.is_absolute():
            return entry_path.resolve()

        return (test_dir_path / entry_path).resolve()

    def discover_in_dir(directory_path: Path) -> list[Path]:
        return sorted(
            path.resolve()
            for path in directory_path.rglob("test_*.py")
            if path.is_file()
        )

    def resolve_entry(entrypath: str | Path, *, list_name: str) -> list[Path]:
        entry_path = make_absolute(entrypath)

        # Explicit file path.
        if entry_path.suffix == ".py":
            if not entry_path.exists():
                raise RuntimeError(
                    f"Unrecognized test file in {list_name}:\n"
                    f"    {entrypath}\n\n"
                    f"Expected file:\n"
                    f"    {entry_path}"
                )

            if not entry_path.is_file():
                raise RuntimeError(
                    f"Entry in {list_name} has .py suffix but is not a file:\n"
                    f"    {entry_path}"
                )

            return [entry_path]

        # No .py suffix: could mean entry.py or entry/.
        file_candidate = entry_path.with_suffix(".py")
        dir_candidate = entry_path

        file_exists = file_candidate.is_file()
        dir_exists = dir_candidate.is_dir()

        if file_exists and not dir_exists:
            return [file_candidate]

        if dir_exists and not file_exists:
            return discover_in_dir(dir_candidate)

        if file_exists and dir_exists:
            print(
                "WARNING: Ambiguous pytest_harness selector.\n"
                f"Both a file and directory match: {entrypath}\n"
                f"Using directory:\n"
                f"    {dir_candidate.relative_to(test_dir_path)}\n"
                f"Use this to select the file explicitly:\n"
                f"    {file_candidate.relative_to(test_dir_path)}"

            )
            return discover_in_dir(dir_candidate)

        raise RuntimeError(
            f"Unrecognized test selector in {list_name}:\n"
            f"    {entrypath}\n\n"
            f"Expected one of:\n"
            f"    {file_candidate}\n"
            f"    {dir_candidate}/"
        )

    # --- include list or discovery ---
    if include_list is None:
        resolved_paths = discover_in_dir(test_dir_path)
    else:
        resolved_paths = []
        for entry in include_list:
            resolved_paths.extend(
                resolve_entry(entry, list_name="include_list")
            )

    # Deduplicate while preserving sorted path order.
    resolved_paths = sorted(set(resolved_paths))

    # --- exclude list ---
    if exclude_list is not None:
        excluded_paths: set[Path] = set()

        for entry in exclude_list:
            excluded_paths.update(
                resolve_entry(entry, list_name="exclude_list")
            )

        resolved_paths = [
            path
            for path in resolved_paths
            if path not in excluded_paths
        ]

    if not resolved_paths:
        raise RuntimeError(
            "No pytest test files selected.\n\n"
            f"Test directory:\n"
            f"    {test_dir_path}\n\n"
            f"include_list:\n"
            f"    {include_list}\n\n"
            f"exclude_list:\n"
            f"    {exclude_list}"
        )

    relative_resolved_paths = [
        path.relative_to(test_dir_path)
        for path in resolved_paths
    ]

    return relative_resolved_paths
