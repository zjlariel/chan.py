# uv package-management design

## Goal

Manage this repository with `uv` while making the existing source tree installable as a Python package.

## Scope

- Add a root `pyproject.toml` with project metadata and a Hatchling build backend.
- Require Python 3.11 or newer, matching the existing virtual environment.
- Declare the runtime packages currently listed in `Script/requirements.txt`: baostock, ipython, matplotlib, numpy, pandas, and requests.
- Include the project’s existing top-level packages and modules in the built distribution without moving source files.
- Add a `dev` dependency group containing pytest.
- Generate `uv.lock` and recreate the broken `.venv` via `uv sync`.

## Package layout

The distribution name will be `chanpy`. Hatchling will explicitly include the source packages already present at repository root and the top-level modules (`Chan.py`, `ChanConfig.py`). Existing imports such as `from Chan import CChan` remain unchanged.

## Operational flow

After implementation, `uv sync` creates a reproducible environment and installs the repository in editable mode. `uv run python main.py` runs the example with that environment, and `uv run pytest` is available for future tests.

## Error handling and verification

The currently checked-in `.venv` cannot launch because its configured uv-managed Python home is missing. `uv sync` is expected to replace it. Verification will include dependency resolution, `uv run python --version`, importing the project’s primary modules, and `uv run pytest`.
