import re
from typing import TYPE_CHECKING

from scibiom_api.transport.request_id import MAX_REQUEST_ID_LENGTH, REQUEST_ID_HEADER

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

GENERATED_ID = re.compile(r"[0-9a-f]{32}")


def test_generates_an_id_when_the_header_is_absent(client: TestClient) -> None:
    response = client.get("/health/live")

    assert GENERATED_ID.fullmatch(response.headers[REQUEST_ID_HEADER])


def test_echoes_a_valid_incoming_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={REQUEST_ID_HEADER: "trace-1.a_B"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-1.a_B"


def test_replaces_an_id_containing_spaces(client: TestClient) -> None:
    response = client.get("/health/live", headers={REQUEST_ID_HEADER: "has spaces"})

    assert GENERATED_ID.fullmatch(response.headers[REQUEST_ID_HEADER])


def test_replaces_an_empty_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={REQUEST_ID_HEADER: ""})

    assert GENERATED_ID.fullmatch(response.headers[REQUEST_ID_HEADER])


def test_accepts_an_id_of_exactly_the_maximum_length(client: TestClient) -> None:
    longest = "a" * MAX_REQUEST_ID_LENGTH

    response = client.get("/health/live", headers={REQUEST_ID_HEADER: longest})

    assert response.headers[REQUEST_ID_HEADER] == longest


def test_replaces_an_id_one_character_over_the_maximum(client: TestClient) -> None:
    overlong = "a" * (MAX_REQUEST_ID_LENGTH + 1)

    response = client.get("/health/live", headers={REQUEST_ID_HEADER: overlong})

    assert GENERATED_ID.fullmatch(response.headers[REQUEST_ID_HEADER])
