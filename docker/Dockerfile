# syntax=docker/dockerfile:1

# --- Application image -------------------------------------------------------
#
# Four stages: base -> build -> tests, and base -> runtime. Tests and runtime
# are separate leaves on purpose, so test tooling can never reach production.
#
# Both base images are pinned by digest. A floating tag means that rebuilding
# the same commit a month later produces a different image. The human-readable
# tag is kept next to the digest; when both are present Docker uses the digest.
#
# The runtime stage has no CMD, EXPOSE or HEALTHCHECK yet: each process the
# image runs (API, relay, workers) adds its entry point together with its code.
#
# Related files:
#   - docker/docker-compose.testing.yml  runs the tests stage
#   - .dockerignore                      what reaches the build context
#   - .github/workflows/ci.yml           the `docker` job builds and scans it
#   - .github/workflows/release.yml      pushes the runtime stage to GHCR
#
# Recipes: `just build`, `just test-container`.


# --- Stage: base -------------------------------------------------------------
# Shared by build and runtime, so a system library added here is present in
# both without being installed twice.

FROM python:3.12-slim-trixie@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS base

ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

# Debian security updates on top of the pinned base. The official image is
# rebuilt only every few weeks, and fixes released in between would otherwise
# fail the vulnerability scan in CI with nothing to do about them but wait.
# The price is that two builds of the same commit may differ in patch levels
# of system packages; the Python layer stays fully pinned.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*


# --- Stage: build ------------------------------------------------------------
# Resolves dependencies and builds the wheel. Nothing from this stage reaches
# the runtime image except the finished virtualenv.

FROM base AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /uvx /usr/local/bin/

ENV \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PYTHON=python3 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    VIRTUAL_ENV=/opt/venv \
    UV_NO_DEV=1
#   UV_PYTHON_DOWNLOADS=0  Use the interpreter from the image, never fetch one.
#   UV_PYTHON=python3      Not python3.12: the base image digest is the single
#                          source of truth for the version.
#   UV_PROJECT_ENVIRONMENT The venv lives outside /app so that a bind mount
#                          over the working directory cannot shadow it.
#   UV_NO_DEV=1            Development groups never enter an image.

WORKDIR /app

# Dependencies are installed before the source is copied, so editing code does
# not invalidate this layer. The lock files are bind-mounted rather than
# copied: they are needed to resolve, not to keep.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

# Build and install the wheel rather than the source tree, so the image
# contains the same artefact that gets published.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv build --wheel --out-dir /tmp/dist && \
    uv pip install --no-deps /tmp/dist/*.whl


# --- Stage: tests ------------------------------------------------------------
# Runs the suite against the built wheel. Used by docker-compose.testing.yml
# and by the `docker` job in CI.

FROM build AS tests

# --no-install-project --inexact keeps the wheel installed above. A plain
# `uv sync` would remove it and reinstall the project in editable mode, so the
# tests would exercise src/ instead of the build artefact.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --inexact --group test

# Without these configs pytest inside the container loses its markers, strict
# flags, warning filters and timeouts — and still reports success.
COPY .pytest.toml .coveragerc ./
COPY tests ./tests

ENV PATH="/opt/venv/bin:${PATH}"

CMD ["pytest"]


# --- Stage: runtime ----------------------------------------------------------
# The image that ships. Built FROM base, not FROM build, so neither uv nor the
# sources are present.

FROM base AS runtime

# A fixed uid/gid keeps file ownership stable across rebuilds, which matters
# for volumes mounted from the host.
ARG APP_UID=10001
ARG APP_GID=10001

RUN groupadd --gid ${APP_GID} --system app \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --system \
        --no-create-home --home-dir /app app \
    && mkdir -p /app \
    && chown app:app /app

COPY --from=build --chown=app:app /opt/venv /opt/venv

ENV \
    PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV="/opt/venv"

WORKDIR /app

# Everything below this line runs unprivileged.
USER app

# Labels for local builds; `just build` fills the arguments in from git. Images
# produced by release.yml get the same labels from docker/metadata-action.
#
# Placed at the end of the stage on purpose: VCS_REF and BUILD_DATE change on
# every build, and higher up they would invalidate the cache for every layer
# below them.
ARG VERSION="0.0.0-local"
ARG VCS_REF="unknown"
ARG BUILD_DATE="1970-01-01T00:00:00Z"

LABEL org.opencontainers.image.title="kop-labworks" \
      org.opencontainers.image.description="Personal blog aggregator" \
      org.opencontainers.image.source="https://github.com/Factorino/kop-labworks" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="python:3.12-slim-trixie" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"
