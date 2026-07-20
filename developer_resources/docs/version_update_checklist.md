PYTEST_HARNESS UPDATE CHECKLIST
===============================

Minor updates on GitHub
-----------------------
Run:

    STAMP=$(date +%Y-%m-%d_%H-%M)

    git status --short --untracked-files=all
    git add .
    git diff --cached --stat
    git commit -m "Update $STAMP"
    git push origin main
    git status


1. Final validation
-------------------
Run:

    example_scripts_runner.py
    linter_runner.py
    pytest_harness_runner.py

Confirm:
- all tests pass
- Ruff, mypy, and Vulture pass
- console and log output look correct
- documentation and examples are current
- the installed Logduo version satisfies the required minimum


2. Update version
-----------------
Update pyproject.toml:

    version = "X.Y.Z"

Confirm the Logduo dependency is current:

    "logduo>=0.1.4",

PyPI versions cannot be replaced after publication.


3. Commit and push
------------------
Run:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')

    echo "$VERSION"
    git status --short --untracked-files=all
    git add .
    git diff --cached --stat
    git commit -m "Release $VERSION"
    git push origin main
    git status

Confirm:
- the displayed version is correct
- the working tree is clean
- GitHub Actions passes on Ubuntu, Windows, and macOS
- do not publish until all required GitHub Actions jobs pass


4. Build distributions
----------------------
Run:

    rm -rf build dist
    find . -maxdepth 2 -type d -name "*.egg-info" -exec rm -rf {} +

    python -m build
    python -m twine check --strict dist/*
    python -m zipfile -l dist/pytest_harness-*.whl
    tar -tzf dist/pytest_harness-*.tar.gz

Confirm the wheel contains:
- the pytest_harness package files
- py.typed
- required package metadata

Confirm the source distribution contains:
- README.md
- LICENSE
- pyproject.toml
- source package files
- intended examples and supporting files


5. Test the local wheel
-----------------------
In the temp project's activated virtual environment, run:

    python -m pip uninstall -y pytest-harness

    python -m pip install --no-deps --force-reinstall \
      "/Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project/dist/"pytest_harness-*.whl

    python -c "from importlib.metadata import version; print('pytest-harness:', version('pytest-harness'))"
    python -c "from importlib.metadata import version; print('logduo:', version('logduo'))"

Confirm:
- the pytest_harness version is correct
- the required Logduo version is installed
- import works
- the basic test runner works
- logs and dashboard output look correct
- no development-project files are required


6. Upload to PyPI
-----------------
Run:

    python -m twine upload dist/*

Use:
- username: __token__
- password: pytest-harness's PyPI API token

The token will not be displayed while typing or pasting it.

Confirm on PyPI:
- the correct version appears
- the README renders correctly
- the wheel and source distribution are present
- metadata and dependencies are correct


7. Test the published package
-----------------------------
In the temp project's activated virtual environment, run:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("/Users/renyawasson/Local/PycharmProjects_local/pytest_harness_project/pyproject.toml", "rb"))["project"]["version"])')

    python -m pip uninstall -y pytest-harness
    python -m pip install --no-cache-dir "pytest-harness==$VERSION"

    python -m pip show pytest-harness
    python -c "from importlib.metadata import version; print('pytest-harness:', version('pytest-harness'))"
    python -c "from importlib.metadata import version; print('logduo:', version('logduo'))"

Run the basic test runner and confirm the published package works correctly.


8. Tag the release
------------------
From the pytest_harness project root, run:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
    TAG="v$VERSION"

    echo "Preparing to create tag: $TAG"

    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "Tag $TAG already exists."
        exit 1
    fi

    git tag "$TAG"
    git push origin "$TAG"


Confirm the tag appears on GitHub.