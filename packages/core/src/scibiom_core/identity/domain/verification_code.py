import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

CODE_LENGTH = 6
CODE_SPACE = 10**CODE_LENGTH


def generate_code() -> str:
    return f"{secrets.randbelow(CODE_SPACE):0{CODE_LENGTH}d}"


def code_mac(secret: bytes, challenge_id: UUID, code: str) -> bytes:
    # The code comes last, so no submitted value can shift the id boundary.
    message = f"{challenge_id}:{code}".encode()
    return hmac.digest(secret, message, hashlib.sha256)
