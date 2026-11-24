from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from scibiom_api.bootstrap.settings import ApiSettings, CorsSettings
from scibiom_api.transport.request_id import REQUEST_ID_HEADER

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "https://evil.example"
ALLOW_ORIGIN_HEADER = "access-control-allow-origin"
ALLOW_METHODS_HEADER = "access-control-allow-methods"
ALLOW_HEADERS_HEADER = "access-control-allow-headers"
ALLOW_CREDENTIALS_HEADER = "access-control-allow-credentials"
EXPOSE_HEADERS_HEADER = "access-control-expose-headers"


@pytest.fixture
def settings(settings: ApiSettings) -> ApiSettings:
    return settings.model_copy(update={"cors": CorsSettings(allowed_origins=(ALLOWED_ORIGIN,))})


def test_allowed_origin_is_echoed(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers[ALLOW_ORIGIN_HEADER] == ALLOWED_ORIGIN


def test_disallowed_origin_gets_no_allow_origin_header(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": DISALLOWED_ORIGIN})

    assert ALLOW_ORIGIN_HEADER not in response.headers


def test_request_id_header_is_exposed_to_browsers(client: TestClient) -> None:
    response = client.get("/health/live", headers={"Origin": ALLOWED_ORIGIN})

    exposed = response.headers[EXPOSE_HEADERS_HEADER].lower().split(", ")
    assert REQUEST_ID_HEADER in exposed


def test_preflight_allows_only_get_with_the_request_id_header_and_no_credentials(
    client: TestClient,
) -> None:
    response = client.options(
        "/health/live",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": f"content-type, {REQUEST_ID_HEADER}",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers[ALLOW_ORIGIN_HEADER] == ALLOWED_ORIGIN
    assert response.headers[ALLOW_METHODS_HEADER] == "GET"
    allowed_headers = response.headers[ALLOW_HEADERS_HEADER].lower().split(", ")
    assert {"content-type", REQUEST_ID_HEADER} <= set(allowed_headers)
    assert ALLOW_CREDENTIALS_HEADER not in response.headers
