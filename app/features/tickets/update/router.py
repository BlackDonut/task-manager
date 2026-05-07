"""チケット更新 Router。

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
from app.features.tickets.update.repository import TicketUpdateRepository
from app.features.tickets.update.schemas import TicketUpdateRequest, TicketUpdateResponse
from app.features.tickets.update.service import TicketUpdateService

logger = get_logger(component="tickets.update")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> TicketUpdateService:
    """依存性注入: DB セッションを受け取り TicketUpdateService を構築して返す。"""
    return TicketUpdateService(TicketUpdateRepository(session))


@router.patch(
    "/{ticket_id}",
    response_model=TicketUpdateResponse,
    status_code=200,
    summary="チケット更新",
    description="既存チケットの編集可能フィールドを一括更新する。product_id は変更不可。",
    dependencies=[permission_required(Actions.UPDATE, Resources.TASK)],
)
async def update_ticket(
    ticket_id: int,
    request: Request,
    body: TicketUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketUpdateService = Depends(_get_service),
) -> TicketUpdateResponse:
    """チケットを更新して更新済みレコードを返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.update.request",
        user_id=user.id,
        ticket_id=ticket_id,
        tracker=body.tracker,
        status=body.status,
        request_id=request_id,
    )

    result = await service.update(ticket_id, body, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "tickets.update.response",
        ticket_id=result.value.id,
        request_id=request_id,
    )
    return result.value
