"""Wiring a policy into SQLAlchemy."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from sqlalchemy import event

from kop.infrastructure.database.common.errors.violations.parser import Backend


if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy import MetaData
    from sqlalchemy.engine.interfaces import Dialect
    from sqlalchemy.orm import DeclarativeBase

    from kop.infrastructure.database.common.errors.violations.policy import ErrorPolicy


def backend_of(dialect: Dialect) -> Backend:
    """Name the backend behind a dialect."""
    return Backend(name=dialect.name, driver=dialect.driver)


def install(engine: Any, policy: ErrorPolicy) -> None:
    """Translate every error this engine raises through `policy`.

    Accepts a sync or an async engine. Returning an exception from SQLAlchemy's
    `handle_error` event replaces the one that would have been raised; returning
    None leaves it untouched, which is what an unrecognised error gets.
    """
    target = getattr(engine, "sync_engine", engine)

    @event.listens_for(target, "handle_error")
    def _translate(context: Any) -> BaseException | None:
        error = context.sqlalchemy_exception or context.original_exception
        return policy.translate(error, backend_of(context.dialect))


def entities_from(base: type[DeclarativeBase], attribute: str = "__entity__") -> dict[str, str]:
    """Collect table-to-entity names off a declarative base.

    A convenience for the common convention of naming the aggregate on the
    model; the policy itself only takes a plain mapping.
    """
    mappers: Iterable[Any] = base.registry.mappers
    names: dict[str, str] = {}
    for mapper in mappers:
        entity = getattr(mapper.class_, attribute, None)
        if isinstance(entity, str) and mapper.local_table is not None:
            names[mapper.local_table.name] = entity
    return names


def metadata_of(base: type[DeclarativeBase]) -> MetaData:
    """The metadata behind a declarative base."""
    return base.metadata
