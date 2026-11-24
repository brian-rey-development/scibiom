from uuid import uuid4

import httpx2
import pytest

from scibiom_core.identity.domain.email import Email
from scibiom_core.identity.ports.email_sender import EmailMessage
from scibiom_infrastructure.email.settings import EmailSettings
from scibiom_infrastructure.email.smtp import SmtpEmailSender

pytestmark = pytest.mark.integration

MAILPIT_API_URL = "http://127.0.0.1:8025/api/v1"
SETTINGS = EmailSettings.model_validate(
    {"host": "127.0.0.1", "port": 1025, "sender": "auth@scibiom.test"}
)


async def test_a_message_sent_through_smtp_arrives_in_mailpit() -> None:
    token = uuid4().hex
    message = EmailMessage(Email("reader@example.com"), f"Your code {token}", "Your code is 123456")

    async with httpx2.AsyncClient(base_url=MAILPIT_API_URL) as mailpit:
        await SmtpEmailSender(SETTINGS).send(message)
        found = (await mailpit.get("/search", params={"query": f"subject:{token}"})).json()
        ids = [summary["ID"] for summary in found["messages"]]
        try:
            received = (await mailpit.get(f"/message/{ids[0]}")).json()
        finally:
            await mailpit.request("DELETE", "/messages", json={"IDs": ids})

    assert len(ids) == 1
    assert received["From"]["Address"] == "auth@scibiom.test"
    assert [to["Address"] for to in received["To"]] == ["reader@example.com"]
    assert received["Subject"] == message.subject
    assert received["Text"].strip() == message.body
