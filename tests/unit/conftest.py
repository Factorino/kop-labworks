"""Fixtures for unit tests.

Unit tests exercise the domain and application layers only, and never reach
outside the process: no network, no database, no filesystem and no clock.
External ports are replaced by stubs and fakes defined here.

Anything that needs a real dependency belongs in ``tests/integration``.
"""
