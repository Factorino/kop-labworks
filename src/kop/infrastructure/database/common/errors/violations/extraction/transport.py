"""Transports: how a driver presents the server's code and message."""

from __future__ import annotations


class DirectTransport:
    """The driver raises the server's error itself. Nothing to undo.

    psycopg does; a driver that wraps the server's error (ODBC, for one) would
    get a transport of its own that restates it first.
    """

    def unwrap(self, error: BaseException) -> BaseException:
        """Return the error unchanged."""
        return error


_DIRECT: DirectTransport = DirectTransport()


def transport_for(driver: str | None) -> DirectTransport:  # noqa: ARG001
    """Pick the transport a driver needs; every supported driver is direct."""
    return _DIRECT
