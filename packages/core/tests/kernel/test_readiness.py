import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scibiom_core.kernel.readiness import (
    CheckOutcome,
    evaluate_readiness,
)

if TYPE_CHECKING:
    import pytest

PRIVATE_DETAIL = "patient-123-secret"
TIMEOUT_SECONDS = 0.05


@dataclass(frozen=True, slots=True)
class PassingCheck:
    name: str = "passing"

    async def probe(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class FailingCheck:
    name: str = "failing"

    async def probe(self) -> None:
        raise ConnectionError(PRIVATE_DETAIL)


@dataclass(frozen=True, slots=True)
class SlowCheck:
    name: str = "slow"

    async def probe(self) -> None:
        await asyncio.Event().wait()


async def test_all_passing_checks_are_ready() -> None:
    report = await evaluate_readiness([PassingCheck("a"), PassingCheck("b")], TIMEOUT_SECONDS)

    assert report.ready
    assert report.outcomes == (CheckOutcome("a", passed=True), CheckOutcome("b", passed=True))


async def test_one_failing_check_makes_report_not_ready() -> None:
    report = await evaluate_readiness([PassingCheck(), FailingCheck()], TIMEOUT_SECONDS)

    assert not report.ready
    assert report.outcomes == (
        CheckOutcome("passing", passed=True),
        CheckOutcome("failing", passed=False),
    )


async def test_check_slower_than_timeout_fails() -> None:
    report = await evaluate_readiness([SlowCheck()], TIMEOUT_SECONDS)

    assert not report.ready
    assert report.outcomes == (CheckOutcome("slow", passed=False),)


async def test_no_checks_is_ready() -> None:
    report = await evaluate_readiness([], TIMEOUT_SECONDS)

    assert report.ready
    assert report.outcomes == ()


async def test_failure_log_names_check_and_error_type_without_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        await evaluate_readiness([FailingCheck()], TIMEOUT_SECONDS)

    (record,) = caplog.records
    assert record.getMessage() == "readiness_check_failed"
    assert getattr(record, "check", None) == "failing"
    assert getattr(record, "error_type", None) == "ConnectionError"
    assert PRIVATE_DETAIL not in caplog.text
    assert record.exc_info is None
