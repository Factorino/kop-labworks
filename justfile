# --- Task runner -------------------------------------------------------------
#
# The single entry point for every operation on the backend. The git hooks run
# the same tools (see .pre-commit-config.yaml), and CI will call these same
# recipes, so a local run and the pipeline cannot drift apart.
#
# `just --list` shows everything. Recipes are grouped; within a group the list
# is sorted alphabetically, so the order in this file only matters to readers.
#
# Caution: with `set shell` below, every line of an ordinary recipe runs in its
# own shell. Variables and traps do not survive between lines — a recipe that
# needs shared state must start with a shebang. Only the last comment line
# before a recipe becomes its description in `just --list`; a blank line
# detaches a comment block from the recipe.


set shell := ["bash", "-euo", "pipefail", "-c"]


# Runs when `just` is called without arguments.
_default:
    @just --list


# --- Dependencies and environment --------------------------------------------
# uv owns the virtualenv; none of these recipes should be replaced by pip.

# Install the locked dependencies; `--locked` fails rather than rewriting uv.lock.
[group('deps')]
sync:
    uv sync --locked

# Re-resolve uv.lock after editing pyproject.toml.
[group('deps')]
lock:
    uv lock

# Install the git hooks declared in .pre-commit-config.yaml.
[group('deps')]
hooks:
    uv run pre-commit install --install-hooks


# --- Static analysis ---------------------------------------------------------
# Configured in .ruff.toml, .mypy.ini and .importlinter.

# Everything read-only: linter, formatter check, types and the layer contract.
[group('lint')]
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src tests
    uv run lint-imports

# Apply the automatic fixes that `lint` only reports.
[group('lint')]
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run every hook over the whole repository.
[group('lint')]
pre-commit:
    uv run pre-commit run --all-files


# --- Tests -------------------------------------------------------------------
# Configured in .pytest.toml and .coveragerc.

# Accepts any pytest arguments: `just test -m unit`, `just test tests/e2e -x`.
[group('test')]
test *args:
    uv run pytest {{ args }}

# Coverage; the source, exclusions and threshold all come from .coveragerc.
[group('test')]
cov *args:
    uv run pytest --cov {{ args }}


# --- Version and changelog ---------------------------------------------------
# Configured in .cz.toml; the release procedure is in CONTRIBUTING.md.

# Compose a Conventional Commit message interactively.
[group('release')]
commit:
    uv run cz commit

# Preview or apply a version bump: `just bump --dry-run`, `just bump --files-only --yes`.
[group('release')]
bump *args:
    uv run cz bump {{ args }}


# --- Cleanup -----------------------------------------------------------------
# Everything this deletes is regenerated on demand, so removing it is safe.

# Every tool cache and build artefact.
[group('clean')]
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache .import_linter_cache \
        .coverage coverage.xml htmlcov dist build
    find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +


# --- Miscellaneous -----------------------------------------------------------

# Aggregate of all local checks; CI runs the same set.
[group('misc')]
check: lint test
