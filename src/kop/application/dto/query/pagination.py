import math
from typing import Annotated, ClassVar, Final, Self

from pydantic import Field, computed_field, model_validator

from kop.application.dto.base import DTO


__all__: list[str] = [
    "DEFAULT_PAGINATION",
    "Page",
    "PageMeta",
    "PageNumber",
    "PageSize",
    "Pagination",
    "TotalCount",
]


# Plain aliases rather than `type` statements, so the constraint appears on the
# property in the OpenAPI schema instead of behind a $ref.

PageNumber = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1, le=100)]
TotalCount = Annotated[int, Field(ge=0)]


class _BasePagination(DTO):
    _abstract_: ClassVar[bool] = True

    page: PageNumber
    page_size: PageSize


class Pagination(_BasePagination):
    page: PageNumber = 1
    page_size: PageSize = 25

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


DEFAULT_PAGINATION: Final[Pagination] = Pagination()


class PageMeta(_BasePagination):
    total: TotalCount

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.page_size)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_prev(self) -> bool:
        return self.page > 1


class Page[DataT](DTO):
    data: tuple[DataT, ...]
    meta: PageMeta

    @model_validator(mode="after")
    def _reject_oversized_page(self) -> Self:
        if len(self.data) > self.meta.page_size:
            raise ValueError(
                f"Page holds {len(self.data)} rows, "
                f"more than the page size of {self.meta.page_size}",
            )
        return self
