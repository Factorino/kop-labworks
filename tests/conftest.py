"""Fixtures and hooks shared by the whole test suite.

Only what every layer needs belongs here; anything specific to one layer goes
into ``tests/<layer>/conftest.py``.

Related files:
    - .pytest.toml: declares the markers applied below.
    - CONTRIBUTING.md: how to point the suite at a database.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.engine import URL, make_url


# The database the integration and end-to-end tests use. Named explicitly
# rather than taken from .config/: a test run must never touch the data of a
# development stack, and the suite must mean the same thing on every machine.
DATABASE_URL_VARIABLE: str = "KOP_TEST_DATABASE_URL"

# Every variable the configuration answers to. `APP__*` overlays config.toml;
# `CONFIG_FILE` names the file itself.
_SETTINGS_PREFIXES: tuple[str, ...] = ("APP__", "CONFIG_FILE")


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Hide the machine the suite happens to run on from every test.

    Without this, whatever the surrounding shell exports — or the
    .config/local.toml a developer has, which is the default path — decides
    the settings a test did not fill in, and the same test means different
    things locally and in CI.
    """
    for name in list(os.environ):
        if name.startswith(_SETTINGS_PREFIXES):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(scope="session")
def database_url() -> URL:
    """The test database, or a skip explaining how to provide one."""
    raw: str | None = os.environ.get(DATABASE_URL_VARIABLE)
    if not raw:
        pytest.skip(f"{DATABASE_URL_VARIABLE} is not set; see CONTRIBUTING.md")
    return make_url(raw)


# Top-level directory inside tests/ -> marker of the same name. This is what
# makes `pytest -m "not e2e"` work without marking every file by hand.
#
# The set must match the `markers` list in .pytest.toml: with --strict-markers
# any divergence fails immediately rather than silently mislabelling tests.
_LAYER_MARKERS: frozenset[str] = frozenset({"unit", "integration", "e2e"})


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Apply the layer marker matching each test's directory."""
    tests_root: Path = Path(__file__).parent
    for item in items:
        try:
            layer: str = item.path.relative_to(tests_root).parts[0]
        except ValueError:
            # A test collected from outside tests/ has no layer to infer.
            continue
        if layer in _LAYER_MARKERS:
            item.add_marker(layer)
