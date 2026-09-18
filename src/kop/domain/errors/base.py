from dataclasses import Field, dataclass, field as dtfield, fields
from string import Formatter
from typing import Any, ClassVar, dataclass_transform, override

from kop.domain.errors.status_code import StatusCode


@dataclass_transform(eq_default=False, kw_only_default=True, field_specifiers=(dtfield,))
def error[ClsT](cls: type[ClsT]) -> type[ClsT]:
    dtcls: type[ClsT] = dataclass(cls, eq=False, kw_only=True)
    _validate_msg_source(dtcls)
    _validate_msg_template(dtcls)
    return dtcls


# With two bases carrying a message template (a kind and a subject) the first
# base wins, so a subject listed first silently replaces the kind's message.
def _validate_msg_source(cls: type[Any]) -> None:
    if "msg" in getattr(cls, "__annotations__", {}):
        return

    templates: dict[type, str] = {
        base: dt_fields["msg"].default
        for base in cls.__bases__
        if "msg" in (dt_fields := getattr(base, "__dataclass_fields__", {}))
    }
    if len(set(templates.values())) < 2:
        return

    first: type = next(iter(templates))
    if "msg" in getattr(first, "__annotations__", {}):
        return

    raise TypeError(
        f"{cls.__name__} takes its message from {first.__name__}, which only "
        f"inherits one, shadowing the template of a later base; order the bases as "
        f"(kind, subject) or declare `msg` explicitly",
    )


def _validate_msg_template(cls: type[Any]) -> None:
    dt_fields: tuple[Field[Any], ...] = fields(cls)
    defaults: dict[str, Any] = {f.name: f.default for f in dt_fields}

    template: Any | None = defaults.get("msg")
    if not isinstance(template, str) or defaults.get("fmt") is False:
        return

    reserved: frozenset[str] = cls._RESERVED_ATTRS
    available: set[str] = {f.name for f in dt_fields} - reserved
    unknown: set[str] = {
        # "{a.b}" and "{a[0]}" resolve through the root name.
        name.split(".", 1)[0].split("[", 1)[0] or "{}"
        for _, name, _, _ in Formatter().parse(template)
        if name is not None
    } - available
    if unknown:
        raise TypeError(
            f"{cls.__name__} message template refers to {sorted(unknown)}, "
            f"which are not fields of the error",
        )


@error
class AppError(Exception):
    _RESERVED_ATTRS: ClassVar[frozenset[str]] = frozenset({"msg", "fmt", "code"})

    code: ClassVar[str] = StatusCode.APP_ERROR
    msg: str = "An error occurred"
    fmt: bool = True

    def __post_init__(self) -> None:
        self.args = (self.fmt_msg,)

    @override
    def __str__(self) -> str:
        return self.fmt_msg

    @property
    def fmt_msg(self) -> str:
        if not self.fmt:
            return self.msg
        return self.msg.format(**self.context)

    @property
    def context(self) -> dict[str, Any]:
        return {
            name: value
            for name, value in self.__dict__.items()
            if name not in self._RESERVED_ATTRS
        }


@error
class DomainError(AppError):
    code: ClassVar[str] = StatusCode.DOMAIN_ERROR
    msg: str = "A domain error occurred"
