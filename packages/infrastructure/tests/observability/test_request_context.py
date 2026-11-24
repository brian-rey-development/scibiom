import pytest

from scibiom_infrastructure.observability.request_context import (
    bound_request_id,
    current_request_id,
)


def test_defaults_to_none() -> None:
    assert current_request_id() is None


def test_bound_value_is_visible_inside_and_reset_after() -> None:
    with bound_request_id("abc"):
        assert current_request_id() == "abc"

    assert current_request_id() is None


def test_nested_binding_restores_outer_value() -> None:
    with bound_request_id("outer"):
        with bound_request_id("inner"):
            assert current_request_id() == "inner"

        assert current_request_id() == "outer"


def _fail_while_bound() -> None:
    with bound_request_id("abc"):
        raise RuntimeError


def test_value_is_reset_when_body_raises() -> None:
    with pytest.raises(RuntimeError):
        _fail_while_bound()

    assert current_request_id() is None
