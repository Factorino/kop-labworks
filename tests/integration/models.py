"""Tables that exist only for the integration tests.

Registered on the application's metadata, like any model, so the naming
convention and the error policy treat them exactly as they will treat real
ones. They are created and dropped by the `schema` fixture and never reach a
migration: autogenerate runs outside the test process.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from kop.infrastructure.database.models.base import BaseORM


class ParentORM(BaseORM):
    __tablename__ = "test_parents"
    __entity__ = "Parent"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)


class ItemORM(BaseORM):
    __tablename__ = "test_items"
    __entity__ = "Item"
    __table_args__ = (CheckConstraint("score >= 0", name="score_non_negative"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("test_parents.id"))
    title: Mapped[str] = mapped_column(String(16), unique=True)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


TABLES: tuple[Table, ...] = (
    BaseORM.metadata.tables[ParentORM.__tablename__],
    BaseORM.metadata.tables[ItemORM.__tablename__],
)
