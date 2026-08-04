PYTEST_HARNESS MINOR UPDATE CHECKLIST (GitHub only)
===================================================
STAMP=$(date +%Y-%m-%d_%H-%M)

git status --short --untracked-files=all
git add .
git diff --cached --stat
git commit -m "Update $STAMP"
git push origin main
git status



PYTEST_HARNESS RELEASE CHECKLIST
================================

I. Local computer checks
========================

A. Local validation (in PyCharm Project window)
-----------------------------------------------
Run:

    examples/basic_project/tests/pytest_harness_runner.py
    developer_resources/pytest_harness_validation/runners/linter_runner.py
    developer_resources/pytest_harness_validation/runners/pytest_harness_validation_runner.py

Use the actual runner paths if their locations differ.

Confirm:

- the basic example runs correctly
- all intended validation tests pass
- expected intentional failures and errors are reported correctly
- Ruff import-order checks pass
- Ruff lint checks pass
- mypy passes
- Vulture passes
- console and log output look correct
- combined coverage looks correct
- per-test-file logs look correct
- import and collection failures are reported correctly
- README and function docstring are current
- README argument names and defaults match `pytest_harness()`
- example runner uses the current public arguments


B. Update package version (in pyproject.toml)
---------------------------------------------
Edit `pyproject.toml`:

    version = "X.Y.Z"

PyPI versions cannot be replaced after publication.



II. GitHub updates (in PyCharm Terminal)
========================================

A. Confirm project directory
----------------------------
    pwd

Expected:

    /Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project


B. Read and save the version from pyproject.toml
------------------------------------------------
    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')

Confirm:

    echo "$VERSION"


C. Review changed files
-----------------------
    git status --short --untracked-files=all

This only displays changes. It does not alter anything.


D. Stage all changes
--------------------
    git add .

This stages modified, new, and deleted files for the next commit.


E. Review staged changes
------------------------
    git diff --cached --stat    # q to exit
    git status --short


F. Commit and push
------------------
    git commit -m "Release $VERSION"
    git push origin main


G. Confirm local and GitHub branches match
------------------------------------------
    git status

Expected:

    On branch main
    Your branch is up to date with 'origin/main'.
    nothing to commit, working tree clean


H. Verify the version stored on GitHub
--------------------------------------
    git fetch origin

    git show origin/main:pyproject.toml | python -c 'import sys, tomllib; print(tomllib.loads(sys.stdin.read())["project"]["version"])'

Expected:

    X.Y.Z


I. Create and push the Git tag
------------------------------
1. Create the tag name:

    TAG="v$VERSION"

2. Confirm the intended tag:

    echo "$TAG"

3. Stop if the tag already exists:

    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "Tag $TAG already exists."
        exit 1
    fi

4. Create and push the tag:

    git tag "$TAG"
    git push origin "$TAG"


J. Create the GitHub Release
----------------------------
Pushing the tag does not necessarily create a GitHub Release.

On GitHub:

1. Open the `pytest_harness` repository.
2. Open Releases.
3. Select Draft a new release.
4. Choose the existing tag `vX.Y.Z`.
5. Use title:

       pytest_harness vX.Y.Z

6. Add release notes or generate them.
7. Make sure it is not marked as a prerelease.
8. Mark it as the latest release.
9. Publish the release.


K. Confirm GitHub Actions
-------------------------
Confirm all required jobs pass on:

- macOS
- Windows
- Ubuntu

Confirm that GitHub Actions runs:

- pytest-harness validation tests
- Ruff
- mypy
- Vulture
- any package-build checks configured in the workflow

Do not publish to PyPI until all required GitHub Actions jobs pass.



III. PyPI release
=================

A. Build the distributions locally
----------------------------------

1. Confirm the project root:

    pwd
    test -f pyproject.toml && echo "Project root confirmed"

Expected path:

    /Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project

Expected confirmation:

    Project root confirmed


2. Read and confirm the package version:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
    echo "$VERSION"

Expected:

    X.Y.Z


3. Remove files from previous builds:

    rm -rf build dist

    find . -maxdepth 3 -type d -name "*.egg-info" -exec rm -rf {} +

This removes generated build files and package metadata. It does not remove
source files.


4. Build the wheel and source distribution:

    python -m build

Expected files:

    dist/pytest_harness-X.Y.Z-py3-none-any.whl
    dist/pytest_harness-X.Y.Z.tar.gz


5. Confirm the expected files were created:

    ls -la dist

Verify that both filenames contain the current version.


6. Validate the distribution metadata:

    python -m twine check --strict dist/*

Expected result for both files:

    PASSED


7. List the contents of the wheel:

    python -m zipfile -l "dist/pytest_harness-$VERSION-py3-none-any.whl"

Confirm the wheel contains:

- the `pytest_harness` package modules
- `py.typed`
- the `pytest_harness-X.Y.Z.dist-info` metadata directory

Confirm important modules are present, including the current equivalents of:

- `__init__.py`
- `pytest_harness.py`
- `arg_resolver.py`
- `constants_and_classes.py`
- `dashboard_builder.py`
- `record_builder.py`
- `resolve_test_file_paths.py`
- `summary_data_builder.py`

Do not expect developer-only files such as:

- tests
- validation runners
- GitHub workflows
- local logs
- build directories


8. Optionally list the source distribution:

    tar -tzf "dist/pytest_harness-$VERSION.tar.gz"

The source distribution normally contains additional project files needed to
build the package. It does not need to match the wheel exactly.


9. Verify the version recorded inside the wheel:

    rm -rf /tmp/pytest_harness_wheel_check

    python -m zipfile -e \
        "dist/pytest_harness-$VERSION-py3-none-any.whl" \
        /tmp/pytest_harness_wheel_check

    grep '^Version:' \
        "/tmp/pytest_harness_wheel_check/pytest_harness-$VERSION.dist-info/METADATA"

Expected:

    Version: X.Y.Z


10. Check required dependency metadata:

    grep '^Requires-Dist:' \
        "/tmp/pytest_harness_wheel_check/pytest_harness-$VERSION.dist-info/METADATA"

Confirm the expected runtime dependencies are present, including:

- pytest
- pytest-cov
- pytest-json-report
- pytest-rerunfailures
- logduo



B. Test the locally built wheel
===============================

Use a clean temporary project or virtual environment so the test cannot
accidentally import `pytest_harness` from the development source directory.


1. Create a clean temporary project:

    rm -rf /tmp/pytest_harness_wheel_test
    mkdir -p /tmp/pytest_harness_wheel_test
    cd /tmp/pytest_harness_wheel_test

    python3.13 -m venv .venv
    source .venv/bin/activate

    python -m pip install --upgrade pip


2. Confirm the active Python:

    which python
    python --version

The path should point into:

    /tmp/pytest_harness_wheel_test/.venv/


3. Set the version from the development project:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("/Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project/pyproject.toml", "rb"))["project"]["version"])')

Confirm:

    echo "$VERSION"


4. Install the exact local wheel:

    python -m pip install \
        "/Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project/dist/pytest_harness-$VERSION-py3-none-any.whl"

Important:

- `VERSION` must be set in this Terminal session.
- Do not put a line break between `pip install` and the wheel path unless using
  the backslash exactly as shown.
- Using the exact wheel filename is safer than using `*.whl`.


5. Confirm the installed package and version:

    python -m pip show pytest-harness

Then:

    python -c 'import importlib.metadata; print(importlib.metadata.version("pytest-harness"))'

Expected:

    X.Y.Z


6. Confirm the import location:

    python -c 'import pytest_harness; print(pytest_harness.__file__)'

The path must point into the temporary virtual environment, not into:

    pytest_harness_project/src


7. Confirm the public function imports:

    python - <<'PY'
    from pytest_harness import pytest_harness

    print(pytest_harness)
    help(pytest_harness)
    PY

Confirm:

- the import succeeds
- the current docstring appears
- all public arguments are documented
- names and defaults match the README


8. Create a small test project:

    mkdir -p basic_project/src/sample_package
    mkdir -p basic_project/tests

    touch basic_project/src/sample_package/__init__.py

    cat > basic_project/src/sample_package/calculator.py <<'PY'
    def add(left: int, right: int) -> int:
        return left + right
    PY

    cat > basic_project/tests/test_calculator.py <<'PY'
    from sample_package.calculator import add


    def test_adds_positive_numbers() -> None:
        result = add(4, 7)
        print(f"add(4, 7) -> {result}")
        assert result == 11
    PY

    cat > basic_project/tests/pytest_harness_runner.py <<'PY'
    from pathlib import Path

    from pytest_harness import pytest_harness


    PROJECT_ROOT = Path(__file__).resolve().parents[1]


    def main() -> None:
        pytest_harness(
            test_file_dir=PROJECT_ROOT / "tests",
            log_dir=PROJECT_ROOT / "tests" / "logs",
            tested_code_dir=PROJECT_ROOT / "src" / "sample_package",
            log_keep=3,
        )


    if __name__ == "__main__":
        main()
    PY


9. Run the installed package:

    cd basic_project/tests
    python pytest_harness_runner.py


10. Confirm the local-wheel workflow:

- the test passes
- the package imports without manually changing `sys.path`
- `sample_package` imports correctly
- total coverage is reported
- source-file coverage is reported
- the dashboard appears
- the summary log is created
- the individual test-file log is created
- the printed value appears in the individual log
- the footer lists generated files
- the process exits with code 0


11. Confirm the installed package is independent of development files.

The workflow must succeed while the current directory is under:

    /tmp/pytest_harness_wheel_test

It must not depend on files inside the development repository.



C. Upload the distributions to PyPI
===================================

Continue only after:

- local validation passes
- GitHub Actions passes
- the GitHub Release is published
- the local wheel workflow passes
- `twine check --strict` passes


1. Return to the project root:

    cd /Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project

Confirm:

    pwd


2. Confirm the distribution files:

    ls -la dist

Expected:

    pytest_harness-X.Y.Z-py3-none-any.whl
    pytest_harness-X.Y.Z.tar.gz


3. Confirm no old distributions are mixed into `dist`:

    find dist -maxdepth 1 -type f -print

Only the two current-version files should be present.


4. Upload both distributions:

    python -m twine upload dist/*

When prompted, use:

    username: __token__
    password: pytest_harness's PyPI API token

The token will not be displayed while it is typed or pasted.


5. Wait for successful upload messages for:

    pytest_harness-X.Y.Z-py3-none-any.whl
    pytest_harness-X.Y.Z.tar.gz

PyPI does not allow an uploaded version to be replaced. If the version already
exists, increment the version, rebuild, retest, and upload the new version.


6. Confirm the release on PyPI.

Check that:

- version `X.Y.Z` appears
- it is the current release
- the README renders correctly
- the short description is correct
- the wheel is present
- the source distribution is present
- `Requires-Python` is correct
- runtime dependencies are correct
- author and project links are correct



D. Test the package published on PyPI
=====================================

Use a new clean environment. Do not reuse the environment containing the
locally installed wheel.


1. Create a clean virtual environment:

    rm -rf /tmp/pytest_harness_pypi_test
    mkdir -p /tmp/pytest_harness_pypi_test
    cd /tmp/pytest_harness_pypi_test

    python3.13 -m venv .venv
    source .venv/bin/activate

    python -m pip install --upgrade pip


2. Set the expected version:

    VERSION="X.Y.Z"

Replace `X.Y.Z` with the published version.


3. Install the exact release from PyPI:

    python -m pip install "pytest-harness==$VERSION"


4. Confirm the installed package:

    python -m pip show pytest-harness

Then:

    python -c 'import importlib.metadata; print(importlib.metadata.version("pytest-harness"))'

Expected:

    X.Y.Z


5. Confirm the package location:

    python -c 'import pytest_harness; print(pytest_harness.__file__)'

The path should point into the clean virtual environment.


6. Confirm the public function and documentation:

    python - <<'PY'
    from pytest_harness import pytest_harness

    print(pytest_harness)
    help(pytest_harness)
    PY


7. Repeat the small-project workflow test from the local-wheel section.

Confirm:

- the package installs with all runtime dependencies
- the runner executes
- tests import the tested package correctly
- the test passes
- coverage is combined correctly
- dashboard output appears
- summary and per-test-file logs are created
- the printed diagnostic value appears in the test-file log
- the process exits with code 0


8. Final confirmation

The release is complete when:

- GitHub shows the correct latest release
- GitHub Actions passes on all required operating systems
- PyPI shows the correct version
- the README and metadata render correctly
- the wheel and source distribution are available
- installation from PyPI succeeds in a clean environment
- `pytest_harness()` imports from the installed package
- the public docstring is current
- a clean example project runs successfully
- imports, coverage, dashboard output, and logs all work correctly