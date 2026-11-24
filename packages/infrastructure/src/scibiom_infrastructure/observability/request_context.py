from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return _request_id.get()


@contextmanager
def bound_request_id(value: str) -> Generator[None]:
    token = _request_id.set(value)
    try:
        yield
    finally:
        _request_id.reset(token)
