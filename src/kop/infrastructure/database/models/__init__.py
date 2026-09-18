from kop.infrastructure.database.models.base import BaseORM


# Importing every model registers its table; autogenerate sees only those.
# Each model module is imported here as it is added.
__all__: list[str] = [
    "BaseORM",
]
