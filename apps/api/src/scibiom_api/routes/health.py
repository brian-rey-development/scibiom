from http import HTTPStatus
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from scibiom_api.transport.dependencies import ReadinessChecksDep, ReadinessTimeoutDep
from scibiom_core.kernel.readiness import ReadinessReport, evaluate_readiness

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]


class CheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: Literal["pass", "fail"]


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "not_ready"]
    checks: tuple[CheckResult, ...]


def _to_readiness_response(report: ReadinessReport) -> ReadinessResponse:
    return ReadinessResponse(
        status="ready" if report.ready else "not_ready",
        checks=tuple(
            CheckResult(name=outcome.name, status="pass" if outcome.passed else "fail")
            for outcome in report.outcomes
        ),
    )


@router.get("/live", operation_id="get_liveness")
async def get_liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/ready",
    operation_id="get_readiness",
    responses={HTTPStatus.SERVICE_UNAVAILABLE.value: {"model": ReadinessResponse}},
)
async def get_readiness(
    checks: ReadinessChecksDep,
    timeout_seconds: ReadinessTimeoutDep,
    response: Response,
) -> ReadinessResponse:
    report = await evaluate_readiness(checks, timeout_seconds)
    if not report.ready:
        response.status_code = HTTPStatus.SERVICE_UNAVAILABLE
    return _to_readiness_response(report)
