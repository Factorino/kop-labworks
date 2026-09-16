"""Infrastructure layer: outbound adapters.

Implementations of the ports declared in ``application`` — database
repositories, message brokers, caches, clients for Telegram and VK.

May import ``application`` and ``domain``. Must not import ``presentation``:
the two are siblings.
"""
