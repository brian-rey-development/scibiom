from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

EMAIL = "ana@example.com"
PROBLEM_MEDIA_TYPE = "application/problem+json"


def _error_locations(response_json: dict[str, list[dict[str, list[str]]]]) -> list[list[str]]:
    return [error["location"] for error in response_json["errors"]]


@pytest.mark.parametrize("code", ["12345", "1234567", "12345a", "١٢٣٤٥٦", "123456\n", ""])
def test_a_code_that_is_not_six_digits_is_rejected(client: TestClient, code: str) -> None:
    response = client.post("/v1/auth/sessions", json={"email": EMAIL, "code": code})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert _error_locations(response.json()) == [["body", "code"]]


@pytest.mark.parametrize("path", ["/v1/auth/codes", "/v1/auth/sessions"])
def test_unexpected_fields_are_rejected(client: TestClient, path: str) -> None:
    response = client.post(path, json={"email": EMAIL, "code": "123456", "role": "admin"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert ["body", "role"] in _error_locations(response.json())


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/auth/codes", {"email": "not-an-email"}),
        ("/v1/auth/sessions", {"email": "not-an-email", "code": "123456"}),
    ],
)
def test_a_malformed_email_is_rejected_before_any_work(
    client: TestClient, path: str, body: dict[str, str]
) -> None:
    response = client.post(path, json=body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "rule_violation"
    assert "not-an-email" not in response.text


def test_an_overlong_email_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/auth/codes", json={"email": f"{'a' * 250}@example.com"})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert _error_locations(response.json()) == [["body", "email"]]
