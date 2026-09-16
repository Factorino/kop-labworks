"""Fixtures and hooks shared by the whole test suite.

Only what every layer needs belongs here; anything specific to one layer goes
into ``tests/<layer>/conftest.py``.

Related files:
    - .pytest.toml: declares the markers applied below.
"""

from pathlib import Path

import pytest


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
