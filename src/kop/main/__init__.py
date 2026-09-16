"""Composition root: wiring and the entry points.

The only place that is allowed to know about every layer at once. Reads the
configuration, constructs the concrete adapters, injects them into the use
cases and starts the processes: the API, the outbox relay and the workers.

Keeping the wiring here is what allows every other layer to depend on
abstractions alone.
"""
