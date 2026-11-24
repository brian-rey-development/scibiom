import json
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, field_validator

from scibiom_api.transport.request_id import REQUEST_ID_HEADER
from scibiom_core.kernel.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    RuleViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from httpx2 import Response

PROBLEM_CONTENT_TYPE = "application/problem+json"
PERSONAL_VALUE = "secret-personal-value"
SUBMITTED_VALUE = "not-a-number-12345"
SUBMITTED_NOTE = "diagnosis-hypertension"
WORKSPACE_NOT_FOUND = "Workspace not found"
UNREGISTERED_STATUS = 499
UNHANDLED_EXCEPTION_MESSAGE = "unhandled_exception"
DOMAIN_ERRORS: dict[str, type[DomainError]] = {
    "not-found": NotFoundError,
    "conflict": ConflictError,
    "rule-violation": RuleViolationError,
    "bare": DomainError,
}


class Submission(BaseModel):
    note: str

    @field_validator("note")
    @classmethod
    def _reject_note(cls, value: str) -> str:
        message = f"bad {value}"
        raise ValueError(message)


def _add_error_routes(app: FastAPI) -> None:
    @app.get("/test/domain-error/{kind}")
    async def domain_error(kind: str) -> None:
        raise DOMAIN_ERRORS[kind](WORKSPACE_NOT_FOUND)

    @app.get("/test/boom")
    async def boom() -> None:
        raise ValueError(PERSONAL_VALUE)


def _add_validation_routes(app: FastAPI) -> None:
    @app.get("/test/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @app.post("/test/submissions")
    async def submit(_submission: Submission) -> None:
        return None


def _add_http_exception_routes(app: FastAPI) -> None:
    @app.get("/test/structured-detail")
    async def structured_detail() -> None:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail={"email": PERSONAL_VALUE})

    @app.get("/test/unregistered-status")
    async def unregistered_status() -> None:
        raise HTTPException(status_code=UNREGISTERED_STATUS, detail="client closed request")


def _add_test_routes(app: FastAPI) -> None:
    _add_error_routes(app)
    _add_validation_routes(app)
    _add_http_exception_routes(app)


def _assert_problem(response: Response, status: int, code: str) -> None:
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_CONTENT_TYPE
    body = response.json()
    assert body["code"] == code
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER]


@pytest.fixture
def problem_client(
    client_with_routes: Callable[[Callable[[FastAPI], None]], TestClient],
) -> TestClient:
    return client_with_routes(_add_test_routes)


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("not-found", HTTPStatus.NOT_FOUND, "not_found"),
        ("conflict", HTTPStatus.CONFLICT, "conflict"),
        ("rule-violation", HTTPStatus.UNPROCESSABLE_CONTENT, "rule_violation"),
        ("bare", HTTPStatus.BAD_REQUEST, "domain_error"),
    ],
)
def test_domain_errors_map_to_problems(
    problem_client: TestClient, kind: str, status: HTTPStatus, code: str
) -> None:
    response = problem_client.get(f"/test/domain-error/{kind}")

    _assert_problem(response, status, code)
    assert response.json()["detail"] == WORKSPACE_NOT_FOUND


def test_unhandled_error_becomes_an_opaque_500_with_request_id(
    problem_client: TestClient,
) -> None:
    response = problem_client.get("/test/boom")

    _assert_problem(response, HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")
    assert PERSONAL_VALUE not in response.text


def test_unhandled_error_is_logged_with_type_and_request_id_but_not_its_message(
    client_with_routes: Callable[[Callable[[FastAPI], None]], TestClient],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Built in the test body because create_app replaces the root log handlers, which must
    # happen after pytest has set up its own capture for this phase.
    response = client_with_routes(_add_test_routes).get("/test/boom")

    output = capsys.readouterr().out
    records = [json.loads(line) for line in output.splitlines()]
    (record,) = [item for item in records if item["message"] == UNHANDLED_EXCEPTION_MESSAGE]
    assert record["exception"]["type"] == "builtins.ValueError"
    assert record["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert PERSONAL_VALUE not in output


def test_validation_error_lists_fields_without_echoing_input(problem_client: TestClient) -> None:
    response = problem_client.get(f"/test/items/{SUBMITTED_VALUE}")

    _assert_problem(response, HTTPStatus.UNPROCESSABLE_CONTENT, "validation_failed")
    errors = response.json()["errors"]
    assert errors[0]["location"] == ["path", "item_id"]
    assert errors[0]["message"] == "Must be an integer"
    assert all("input" not in error for error in errors)
    assert SUBMITTED_VALUE not in response.text


def test_validator_messages_that_echo_input_are_replaced_with_static_text(
    problem_client: TestClient,
) -> None:
    response = problem_client.post("/test/submissions", json={"note": SUBMITTED_NOTE})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    (error,) = response.json()["errors"]
    assert error["type"] == "value_error"
    assert error["message"] == "Invalid value"
    assert SUBMITTED_NOTE not in response.text


def test_unknown_route_becomes_a_404_problem_with_request_id(problem_client: TestClient) -> None:
    response = problem_client.get("/does-not-exist")

    _assert_problem(response, HTTPStatus.NOT_FOUND, "not_found")


def test_method_not_allowed_keeps_the_allow_header(problem_client: TestClient) -> None:
    response = problem_client.post("/health/live")

    _assert_problem(response, HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")
    assert "GET" in response.headers["allow"]


def test_structured_http_exception_detail_is_not_exposed(problem_client: TestClient) -> None:
    response = problem_client.get("/test/structured-detail")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "detail" not in response.json()
    assert PERSONAL_VALUE not in response.text


def test_unregistered_status_code_gets_a_generic_problem(problem_client: TestClient) -> None:
    response = problem_client.get("/test/unregistered-status")

    _assert_problem(response, UNREGISTERED_STATUS, "http_error")
    body = response.json()
    assert body["title"] == "Error"
    assert body["detail"] == "client closed request"
