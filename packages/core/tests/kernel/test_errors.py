from typing import TYPE_CHECKING

import pytest

from scibiom_core.kernel.errors import DomainError

if TYPE_CHECKING:
    from collections.abc import Iterator


def _subclasses(base: type[DomainError]) -> Iterator[type[DomainError]]:
    for subclass in base.__subclasses__():
        yield subclass
        yield from _subclasses(subclass)


ALL_ERRORS = (DomainError, *_subclasses(DomainError))


def test_codes_are_distinct() -> None:
    codes = [error.code for error in ALL_ERRORS]

    assert len(set(codes)) == len(codes)


@pytest.mark.parametrize("error_type", ALL_ERRORS)
def test_message_is_preserved(error_type: type[DomainError]) -> None:
    error = error_type("something went wrong")

    assert error.message == "something went wrong"
    assert str(error) == "something went wrong"
