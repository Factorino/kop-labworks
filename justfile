# --- Task runner -------------------------------------------------------------
#
# The single entry point for every operation on the backend. The git hooks run
# the same tools (see .pre-commit-config.yaml), and CI calls these same
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


# --- Variables ---------------------------------------------------------------
# `--env-file` names what compose interpolates into the stack files; without
# it compose would read docker/.env, and everything to fill in should be under
# .config/. See .config/compose.env.example.

compose := "docker compose --env-file .config/compose.env -f docker/docker-compose.yml"
compose_dev := "docker compose --env-file .config/compose.env -f docker/docker-compose.dev.yml"
compose_tests := "docker compose -f docker/docker-compose.tests.yml"
image := "kop-labworks"


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

# Bootstrap a working copy: dependencies plus configs and secrets from the *.example files.
[group('deps')]
init: sync
    #!/usr/bin/env bash
    set -euo pipefail
    # dotglob is required: without it the glob would skip a dotfile template.
    shopt -s dotglob nullglob
    mkdir -p .config .secrets
    # The directory, not the files, keeps other host users out: compose
    # bind-mounts each secret with its host mode, and a container user is not
    # the owner, so the files themselves must stay readable.
    chmod 700 .secrets
    for example in .config/*.example .secrets/*.example; do
        target="${example%.example}"
        # Never overwrite a file that already holds real values.
        if [[ -e "${target}" ]]; then
            echo "skip    ${target}"
            continue
        fi
        cp "${example}" "${target}"
        if [[ "${example}" == .secrets/* ]]; then
            chmod 644 "${target}"
        fi
        echo "created ${target}"
    done
    echo
    echo "Replace the change-me values in .config/ and .secrets/ before 'just up'."


# --- Static analysis ---------------------------------------------------------
# Configured in .ruff.toml, .mypy.ini and .importlinter.

# Everything read-only: linter, formatter check, types and the layer contract.
[group('lint')]
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src tests scripts
    uv run lint-imports

# Apply the automatic fixes that `lint` only reports.
[group('lint')]
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run every hook over the whole repository, exactly as the CI `lint` job does.
[group('lint')]
pre-commit:
    uv run pre-commit run --all-files

# `--disable-pip` works because the export carries hashes; nothing is installed.

# Audit every locked dependency for known vulnerabilities. Needs network.
[group('lint')]
audit:
    uv export --frozen --no-emit-project --all-groups --format requirements.txt | uv run pip-audit --disable-pip --requirement /dev/stdin


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

# The reports CI keeps as artefacts: JUnit XML, coverage XML and HTML.
[group('test')]
test-report *args:
    uv run pytest --cov --cov-report=term --cov-report=xml --cov-report=html --junitxml=junit.xml {{ args }}

# Run the tests inside the image next to disposable dependencies, then remove them.
[group('test')]
test-container:
    #!/usr/bin/env bash
    # A shebang recipe on purpose: just runs each line of an ordinary recipe in
    # a separate shell, so the trap would fire immediately, before `up`, and
    # the cleanup would never happen.
    set -euo pipefail
    trap '{{ compose_tests }} down -v --remove-orphans' EXIT
    {{ compose_tests }} up --build --abort-on-container-exit --exit-code-from app-tests


# --- Container stack ---------------------------------------------------------
# Wraps docker/docker-compose.yml. Requires `just init` first: the stack reads
# .config/compose.env and the secrets under .secrets/, neither of which is in
# the repository.

# The fallbacks matter: `git rev-parse` fails in a repository without commits.

# Build the runtime image, stamping the OCI labels from git.
[group('stack')]
build *args:
    docker build -f docker/Dockerfile --target runtime \
        --build-arg VERSION="$(git describe --tags --always 2>/dev/null || echo unknown)" \
        --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        -t {{ image }}:local {{ args }} .

# Start the stack in the background and wait until every service is healthy.
[group('stack')]
up *args:
    {{ compose }} up -d --wait {{ args }}

# Same as `up`, but for a single service: `just service app-db-pg`.
[group('stack')]
service name *args:
    {{ compose }} up -d --wait {{ name }} {{ args }}

[group('stack')]
restart *args:
    {{ compose }} restart {{ args }}

[group('stack')]
ps:
    {{ compose }} ps

[group('stack')]
logs *args:
    {{ compose }} logs -f --tail=100 {{ args }}

# Stop the stack. Volumes survive; use `teardown` to drop them.
[group('stack')]
down *args:
    {{ compose }} down {{ args }}


# --- Development dependencies ------------------------------------------------
# Postgres, Redis and RabbitMQ on 127.0.0.1 for processes run on the host.
# Separate from the application stack, whose services have no port on the host.

# Start the development dependencies and wait until they are healthy.
[group('dev')]
dev-up:
    {{ compose_dev }} up -d --wait

# Stop the development dependencies; add `-v` to drop their data as well.
[group('dev')]
dev-down *args:
    {{ compose_dev }} down {{ args }}


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

# Write docs/metrics/<version>.json and the summary table: `just metrics v0.2.0`.
[group('release')]
metrics version *args:
    uv run python -m scripts.metrics {{ version }} {{ args }}


# --- Cleanup -----------------------------------------------------------------
# Everything this deletes is regenerated on demand, so removing it is safe.

# Remove the application and test stacks together with their volumes.
[group('clean')]
teardown:
    {{ compose }} down -v --remove-orphans
    {{ compose_tests }} down -v --remove-orphans

# Every tool cache and build artefact. Separate from `teardown`, so it works without Docker.
[group('clean')]
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache .import_linter_cache \
        .coverage coverage.xml junit.xml htmlcov dist build
    find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +


# --- Miscellaneous -----------------------------------------------------------

# Aggregate of all local checks; CI runs the same set.
[group('misc')]
check: lint test
