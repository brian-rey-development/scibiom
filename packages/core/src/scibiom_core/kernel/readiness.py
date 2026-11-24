import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class ReadinessCheck(Protocol):
    @property
    def name(self) -> str: ...

    async def probe(self) -> None:
        """Return normally when the dependency is usable, raise otherwise."""
        ...


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    name: str
    passed: bool


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    outcomes: tuple[CheckOutcome, ...]

    @property
    def ready(self) -> bool:
        return all(outcome.passed for outcome in self.outcomes)


async def evaluate_readiness(
    checks: Sequence[ReadinessCheck], timeout_seconds: float
) -> ReadinessReport:
    outcomes = await asyncio.gather(*(_run_check(check, timeout_seconds) for check in checks))
    return ReadinessReport(outcomes=tuple(outcomes))


async def _run_check(check: ReadinessCheck, timeout_seconds: float) -> CheckOutcome:
    try:
        async with asyncio.timeout(timeout_seconds):
            await check.probe()
    except Exception as error:  # noqa: BLE001 - any probe failure means not ready
        logger.warning(
            "readiness_check_failed",
            extra={"check": check.name, "error_type": type(error).__name__},
        )
        return CheckOutcome(name=check.name, passed=False)
    else:
        return CheckOutcome(name=check.name, passed=True)
