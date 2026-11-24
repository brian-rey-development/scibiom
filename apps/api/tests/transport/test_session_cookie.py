from datetime import timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi import Request, Response

from scibiom_api.bootstrap.settings import HARDENED_ENVIRONMENTS, Environment
from scibiom_api.transport.session_cookie import read_session_cookie, set_session_cookie

SESSION_VALUE = "opaque-session-token"
MAX_AGE = timedelta(hours=5)
LOCAL_ENVIRONMENTS = sorted(set(Environment) - HARDENED_ENVIRONMENTS)
HARDENED = sorted(HARDENED_ENVIRONMENTS)


def _written_cookie(environment: Environment) -> SimpleCookie:
    response = Response()
    set_session_cookie(response, SESSION_VALUE, environment, MAX_AGE)
    return SimpleCookie(response.headers["set-cookie"])


@pytest.mark.parametrize("environment", LOCAL_ENVIRONMENTS)
def test_local_environments_use_a_plain_cookie(environment: Environment) -> None:
    cookie = _written_cookie(environment)

    morsel = cookie["scibiom_session"]
    assert morsel.value == SESSION_VALUE
    assert not morsel["secure"]


@pytest.mark.parametrize("environment", HARDENED)
def test_hardened_environments_use_a_host_prefixed_secure_cookie(environment: Environment) -> None:
    cookie = _written_cookie(environment)

    morsel = cookie["__Host-scibiom_session"]
    assert morsel.value == SESSION_VALUE
    assert morsel["secure"]
    assert not morsel["domain"]


@pytest.mark.parametrize("environment", Environment)
def test_every_environment_scopes_the_cookie_to_the_site_for_the_given_lifetime(
    environment: Environment,
) -> None:
    morsel = next(iter(_written_cookie(environment).values()))

    assert morsel["httponly"]
    assert morsel["samesite"].lower() == "strict"
    assert morsel["path"] == "/"
    assert morsel["max-age"] == str(int(MAX_AGE.total_seconds()))
    assert not morsel["domain"]


def _request_with_cookie(name: str) -> Request:
    header = f"{name}={SESSION_VALUE}".encode()
    return Request({"type": "http", "headers": [(b"cookie", header)]})


@pytest.mark.parametrize("environment", Environment)
def test_the_cookie_written_for_an_environment_is_the_one_read_back(
    environment: Environment,
) -> None:
    [name] = _written_cookie(environment)

    assert read_session_cookie(_request_with_cookie(name), environment) == SESSION_VALUE


@pytest.mark.parametrize("environment", Environment)
def test_a_request_without_the_environments_cookie_has_no_session(
    environment: Environment,
) -> None:
    other = "scibiom_session" if environment in HARDENED_ENVIRONMENTS else "__Host-scibiom_session"

    assert read_session_cookie(_request_with_cookie(other), environment) is None
