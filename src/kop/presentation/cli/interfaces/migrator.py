"""What the `db` commands need from a migration tool.

Declared next to the code that calls it rather than in the layer that
implements it: the adapter in `infrastructure` satisfies this protocol
structurally and imports nothing from presentation. The two meet in `main`,
which is also where a mismatch would be reported.
"""

from abc import abstractmethod
from typing import Protocol


class IMigrator(Protocol):
    @abstractmethod
    def upgrade(self, revision: str) -> None: ...

    @abstractmethod
    def downgrade(self, revision: str) -> None: ...

    @abstractmethod
    def revision(self, message: str, *, autogenerate: bool) -> None: ...

    @abstractmethod
    def current(self) -> str | None: ...
