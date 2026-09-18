from typing import ClassVar

import pytest

from kop.application.errors.common import NotFoundError
from kop.domain.errors.base import AppError, DomainError, error
from kop.domain.errors.common import ValidationError


def test_message_is_formatted_from_fields() -> None:
    exception = ValidationError(field="title", reason="is empty")

    assert str(exception) == "Field 'title' validation error: is empty"
    assert exception.args == ("Field 'title' validation error: is empty",)


def test_context_holds_fields_without_reserved_attributes() -> None:
    exception = NotFoundError(entity="Post", value=42)

    assert exception.context == {"entity": "Post", "field": "id", "value": 42}


def test_unformatted_message_is_kept_verbatim() -> None:
    exception = AppError(msg="literal {braces}", fmt=False)

    assert str(exception) == "literal {braces}"


def test_code_identifies_the_error_class() -> None:
    assert ValidationError(field="x").code == "validation_error"
    assert DomainError().code == "domain_error"


def test_template_referring_to_unknown_field_is_rejected() -> None:
    with pytest.raises(TypeError, match=r"refers to \['missing'\]"):

        @error
        class BrokenError(DomainError):
            msg: str = "{missing} happened"


def test_shadowed_template_of_later_base_is_rejected() -> None:
    @error
    class KindError(DomainError):
        msg: str = "kind message"

    @error
    class SubjectError(DomainError):
        msg: str = "subject message"

    @error
    class InheritsOnlyError(SubjectError):
        code: ClassVar[str] = "inherits_only"

    with pytest.raises(TypeError, match="order the bases"):

        @error
        class CombinedError(InheritsOnlyError, KindError):
            pass
