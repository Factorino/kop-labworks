"""Presentation layer: inbound adapters.

Everything through which the outside world reaches the application — HTTP
handlers, CLI commands, message consumers. Translates external input into use
case calls and their results back out.

May import ``application`` and ``domain``. Must not import
``infrastructure``: the two are siblings.
"""
