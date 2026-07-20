LOGDUO UPDATE CHECKLIST
=======================
minor updates on GitHub:

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


2. Update version
-----------------
Update pyproject.toml:

    version = "X.Y.Z"

PyPI versions cannot be replaced after publication.


3. Commit and push
------------------
Run:

    VERSION=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
    git status --short --untracked-files=all
    git add .
    git diff --cached --stat
    git commit -m "Release $VERSION"
    git push origin main
    git status
    echo "$VERSION"

Confirm:
- working tree is clean
- GitHub Actions passes on Ubuntu, Windows, and macOS
- Do not publish until all required GitHub Actions jobs pass.


4. Build distributions
----------------------
Run:

    rm -rf build dist
    find . -maxdepth 2 -type d -name "*.egg-info" -exec rm -rf {} +
    python -m build
    python -m twine check --strict dist/*
    python -m zipfile -l dist/logduo-*.whl
    

Confirm the wheel contains:
- Logduo package files
- py.typed
- README and examples
- required package data
- package metadata


5. Test the local wheel
-----------------------
Install the wheel in a clean virtual environment
- Delete logduo from temp_project then reinstall using:

    python -m pip uninstall -y logduo
    python -m pip install "/Users/renyawasson/Local/PycharmProjects_local/logduo_project/dist/"logduo-*.whl

Confirm:
- import works
- package version is correct
- basic logging works
- documentation export works
- no development-project files are required


6. Upload to PyPI
-----------------
Run:

    python -m twine upload dist/*

Use:
- username: __token__
- password: Logduo's PyPI API token 

The token will not be displayed while typing or pasting it.

Confirm on PyPI:
- correct version appears
- README renders correctly
- wheel and source distribution are present
- metadata is correct


7. Test the published package
-----------------------------
In a clean environment:

    python -m pip install --upgrade logduo
    python -m pip show logduo

Run a basic logging test.


8. Tag the release
------------------
Run:

    git tag vX.Y.Z
    git push origin vX.Y.Z

Confirm the tag appears on GitHub.

