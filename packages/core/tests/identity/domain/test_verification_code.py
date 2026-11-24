import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING
from uuid import UUID

from scibiom_core.identity.domain.verification_code import (
    CODE_SPACE,
    code_mac,
    generate_code,
)

if TYPE_CHECKING:
    import pytest

SECRET = b"s" * 32
CHALLENGE_ID = UUID("0192f3a0-0000-7000-8000-000000000001")
CODE = "482913"


def test_generated_code_draws_from_every_six_digit_value_and_keeps_leading_zeros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bounds: list[int] = []

    def draw(bound: int) -> int:
        bounds.append(bound)
        return 7

    monkeypatch.setattr(secrets, "randbelow", draw)

    assert generate_code() == "000007"
    assert bounds == [CODE_SPACE] == [1_000_000]


def test_code_mac_is_the_hmac_sha256_of_the_id_and_code() -> None:
    expected = hmac.new(SECRET, f"{CHALLENGE_ID}:{CODE}".encode(), hashlib.sha256).digest()

    assert code_mac(SECRET, CHALLENGE_ID, CODE) == expected
