from dataclasses import FrozenInstanceError

import pytest

from kop.domain.value_objects.base import ValueObject, value_object


@value_object
class Title(ValueObject):
    value: str


class Undecorated(ValueObject):
    value: str


def test_base_value_object_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        ValueObject()


def test_subclass_without_decorator_is_rejected() -> None:
    with pytest.raises(TypeError, match="missing the @value_object decorator"):
        Undecorated()


def test_value_object_without_fields_is_rejected() -> None:
    with pytest.raises(TypeError, match="at least one field"):

        @value_object
        class Empty(ValueObject):
            pass


def test_value_objects_compare_by_value() -> None:
    assert Title(value="a") == Title(value="a")
    assert Title(value="a") != Title(value="b")


def test_value_object_is_immutable() -> None:
    title = Title(value="a")

    with pytest.raises(FrozenInstanceError):
        title.value = "b"  # type: ignore[misc]
