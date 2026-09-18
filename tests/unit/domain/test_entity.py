from uuid import UUID, uuid4

import pytest

from kop.domain.entities.base import Entity, entity


@entity
class Item(Entity[UUID]):
    title: str


@entity
class Other(Entity[UUID]):
    title: str


def test_base_entity_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        Entity(id=uuid4())


def test_entities_are_equal_by_type_and_id() -> None:
    item_id = uuid4()

    assert Item(id=item_id, title="a") == Item(id=item_id, title="b")
    assert Item(id=item_id, title="a") != Item(id=uuid4(), title="a")
    assert Item(id=item_id, title="a") != Other(id=item_id, title="a")
    assert Item(id=item_id, title="a") != item_id


def test_hash_follows_equality() -> None:
    item_id = uuid4()

    assert len({Item(id=item_id, title="a"), Item(id=item_id, title="b")}) == 1


def test_id_cannot_be_changed() -> None:
    item = Item(id=uuid4(), title="a")

    with pytest.raises(AttributeError, match="not permitted"):
        item.id = uuid4()


def test_other_fields_can_be_changed() -> None:
    item = Item(id=uuid4(), title="a")

    item.title = "b"

    assert item.title == "b"
