"""What happens to the errors the policy deliberately left alone.

Constraint violations never reach here. The `handle_error` hook installed on
the engine has already replaced them with domain and application errors, which
are not `SQLAlchemyError` and pass straight through the guard below. What is
left is a lost connection, a timeout, a statement that will not compile —
infrastructure, not something a caller can act on field by field.

So this exists for one reason: no `sqlalchemy.exc` type may leave the
infrastructure layer. The layer contract in `.importlinter` cannot see that far
— an exception crosses a boundary without anyone importing it.

The ORM's own `NoResultFound` and `MultipleResultsFound` are deliberately not
handled. They are raised while a `Result` is being consumed, which happens
after `_execute` has returned, so they never pass through the decorator; a
reader that wants a missing row to mean something raises for itself.

Related files:
  - policy.py  the rules that translate every violation, before this runs
"""

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, NoReturn

from sqlalchemy.exc import SQLAlchemyError
import structlog

from kop.infrastructure.errors.base import InfrastructureError


__all__: list[str] = ["handle_sqlalchemy_error", "handle_sqlalchemy_errors"]

_logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(__name__)


def handle_sqlalchemy_error(exception: SQLAlchemyError) -> NoReturn:
    """Restate a database failure as an infrastructure error of ours."""
    _logger.error("database.unexpected_error", exc_info=exception)
    raise InfrastructureError from exception


def handle_sqlalchemy_errors[**P, R](
    wrapped: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, Coroutine[Any, Any, R]]:
    """The same translation, as a decorator for an async method."""

    @wraps(wrapped)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await wrapped(*args, **kwargs)
        except SQLAlchemyError as exception:
            handle_sqlalchemy_error(exception)

    return wrapper
