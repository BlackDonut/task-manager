"""チケット作成 Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Service 層に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.create.repository import TicketCreateRepository
from app.features.tickets.create.schemas import TicketCreateRequest, TicketCreateResponse
from app.features.tickets.create.service import TicketCreateService

logger = get_logger(component="tickets.create")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> TicketCreateService:
    """依存性注入: DB セッションを受け取り TicketCreateService を構築して返す。"""
    return TicketCreateService(TicketCreateRepository(session))


@router.post(
    "",
    response_model=TicketCreateResponse,
    status_code=201,
    summary="チケット作成",
    description="新規チケットを作成する。",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def create_ticket(
    request: Request,
    body: TicketCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketCreateService = Depends(_get_service),
) -> TicketCreateResponse:
    """新規チケットを作成して作成済みレコードを返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.create.request",
        user_id=user.id,
        product_id=body.product_id,
        tracker=body.tracker,
        request_id=request_id,
    )

    result = await service.create(body, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "tickets.create.response",
        user_id=user.id,
        ticket_id=result.value.id,
        request_id=request_id,
    )
    return result.value
