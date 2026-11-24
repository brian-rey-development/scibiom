from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scibiom_api.bootstrap.settings import ApiSettings
from scibiom_core.identity.use_cases.request_sign_in_code import RequestSignInCode
from scibiom_core.identity.use_cases.resolve_session import ResolveSession
from scibiom_core.identity.use_cases.verify_sign_in_code import VerifySignInCode
from scibiom_core.kernel.clock import SystemClock
from scibiom_infrastructure.database.engine import create_database_engine
from scibiom_infrastructure.database.readiness import DatabaseReadinessCheck
from scibiom_infrastructure.database.repositories.identity.transaction import (
    SqlIdentityTransactions,
)
from scibiom_infrastructure.email.smtp import SmtpEmailSender

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from scibiom_core.kernel.readiness import ReadinessCheck


@dataclass(frozen=True, slots=True)
class Container:
    settings: ApiSettings
    engine: AsyncEngine
    readiness_checks: tuple[ReadinessCheck, ...]
    request_sign_in_code: RequestSignInCode
    verify_sign_in_code: VerifySignInCode
    resolve_session: ResolveSession


type ContainerFactory = Callable[[ApiSettings], Container]


def build_container(settings: ApiSettings) -> Container:
    engine = create_database_engine(settings.database)
    transactions = SqlIdentityTransactions(engine)
    clock = SystemClock()
    code_secret = settings.identity.secret.get_secret_value().encode()
    return Container(
        settings=settings,
        engine=engine,
        readiness_checks=(DatabaseReadinessCheck(engine),),
        request_sign_in_code=RequestSignInCode(
            transactions, SmtpEmailSender(settings.email), clock, code_secret
        ),
        verify_sign_in_code=VerifySignInCode(transactions, clock, code_secret),
        resolve_session=ResolveSession(transactions, clock),
    )


async def dispose_container(container: Container) -> None:
    await container.engine.dispose()
