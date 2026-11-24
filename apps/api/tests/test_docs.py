from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from scibiom_api.bootstrap.settings import HARDENED_ENVIRONMENTS, Environment
from scibiom_api.main import create_app

if TYPE_CHECKING:
    from collections.abc import Callable

    from scibiom_api.bootstrap.settings import ApiSettings

HARDENED_DATABASE_URL = (
    "postgresql+psycopg://user:pass@db.internal:5432/scibiom?sslmode=verify-full"
)
HTTPS_ORIGIN = "https://scibiom.example"


@pytest.mark.parametrize("environment", sorted(HARDENED_ENVIRONMENTS))
def test_docs_are_disabled_in_hardened_environments(
    settings_factory: Callable[[Environment, tuple[str, ...], str], ApiSettings],
    environment: Environment,
) -> None:
    hardened = settings_factory(environment, (HTTPS_ORIGIN,), HARDENED_DATABASE_URL)

    with TestClient(create_app(hardened)) as client:
        assert client.get("/docs").status_code == HTTPStatus.NOT_FOUND
        assert client.get("/openapi.json").status_code == HTTPStatus.NOT_FOUND


def test_docs_are_enabled_in_test(client: TestClient) -> None:
    assert client.get("/docs").status_code == HTTPStatus.OK
