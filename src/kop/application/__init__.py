"""Application layer: use cases and the ports they depend on.

Orchestrates the domain to fulfil a use case. Talks to the outside world only
through ports declared here as abstractions; the implementations live in
``infrastructure``.

May import ``domain``, and nothing else from the package.
"""
