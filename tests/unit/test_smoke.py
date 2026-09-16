"""Smoke test: the package is installed and importable.

Deliberately trivial. Its job is to fail loudly when packaging breaks — a bad
wheel, a missing dependency group, or a container image built without the
project installed.
"""

import importlib

import pytest

import kop


def test_package_is_importable() -> None:
    assert kop.__name__ == "kop"


@pytest.mark.parametrize(
    "layer",
    ["domain", "application", "infrastructure", "presentation", "main"],
)
def test_layer_is_importable(layer: str) -> None:
    module = importlib.import_module(f"kop.{layer}")
    assert module.__doc__
