from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from scibiom_api.bootstrap.settings import ApiSettings, CorsSettings
from scibiom_api.transport.request_id import REQUEST_ID_HEADER

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "https://evil.example"
NULL_ORIGIN = "null"
ROUTE_PATH = "/test/origin"
UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
ALLOW_ORIGIN_HEADER = "access-control-allow-origin"
PROBLEM_CONTENT_TYPE = "application/problem+json"


@pytest.fixture
def settings(settings: ApiSettings) -> ApiSettings:
    return settings.model_copy(update={"cors": CorsSettings(allowed_origins=(ALLOWED_ORIGIN,))})


@pytest.fixture
def route_calls() -> list[str]:
    return []


@pytest.fixture
def origin_client(
    client_with_routes: Callable[[Callable[[FastAPI], None]], TestClient],
    route_calls: list[str],
) -> TestClient:
    def add_routes(app: FastAPI) -> None:
        @app.api_route(ROUTE_PATH, methods=["GET", *UNSAFE_METHODS])
        async def record() -> None:
            route_calls.append("called")

    return client_with_routes(add_routes)


@pytest.mark.parametrize("method", UNSAFE_METHODS)
def test_disallowed_origin_is_rejected_before_the_route(
    origin_client: TestClient, route_calls: list[str], method: str
) -> None:
    response = origin_client.request(method, ROUTE_PATH, headers={"Origin": DISALLOWED_ORIGIN})

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers["content-type"] == PROBLEM_CONTENT_TYPE
    body = response.json()
    assert body["code"] == "forbidden"
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert DISALLOWED_ORIGIN not in response.text
    assert route_calls == []


def test_null_origin_is_rejected(origin_client: TestClient, route_calls: list[str]) -> None:
    response = origin_client.post(ROUTE_PATH, headers={"Origin": NULL_ORIGIN})

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert route_calls == []


def test_one_disallowed_origin_among_several_is_rejected(
    origin_client: TestClient, route_calls: list[str]
) -> None:
    response = origin_client.post(
        ROUTE_PATH, headers=[("Origin", ALLOWED_ORIGIN), ("Origin", DISALLOWED_ORIGIN)]
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert route_calls == []


@pytest.mark.parametrize("method", UNSAFE_METHODS)
def test_allowed_origin_reaches_the_route(
    origin_client: TestClient, route_calls: list[str], method: str
) -> None:
    response = origin_client.request(method, ROUTE_PATH, headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == HTTPStatus.OK
    assert route_calls == ["called"]


def test_absent_origin_reaches_the_route(origin_client: TestClient, route_calls: list[str]) -> None:
    response = origin_client.post(ROUTE_PATH)

    assert response.status_code == HTTPStatus.OK
    assert route_calls == ["called"]


def test_safe_method_with_a_foreign_origin_passes_without_cors_headers(
    origin_client: TestClient, route_calls: list[str]
) -> None:
    response = origin_client.get(ROUTE_PATH, headers={"Origin": DISALLOWED_ORIGIN})

    assert response.status_code == HTTPStatus.OK
    assert ALLOW_ORIGIN_HEADER not in response.headers
    assert route_calls == ["called"]
