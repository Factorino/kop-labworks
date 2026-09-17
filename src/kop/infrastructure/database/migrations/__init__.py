"""Alembic environment and revisions.

Shipped inside the package rather than next to it: the runtime image carries
the built wheel and nothing else, so migrations that lived at the repository
root would not exist where they have to run. `kop-cli db upgrade` locates them
by package, which is also why there is no alembic.ini.
"""
