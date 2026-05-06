"""ガントチャート Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Service 層に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.gantt.repository import GanttTicketRepository
from app.features.tickets.gantt.schemas import GanttTicketListResponse, GanttTicketQuery
from app.features.tickets.gantt.service import GanttTicketService
from app.features.tickets.list.schemas import TicketPriority, TicketStatus, TicketTracker

logger = get_logger(component="tickets.gantt")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> GanttTicketService:
    """依存性注入: DB セッションを受け取り GanttTicketService を構築して返す。"""
    return GanttTicketService(GanttTicketRepository(session))


@router.get(
    "/gantt",
    response_model=GanttTicketListResponse,
    summary="ガントチャート用チケット一覧取得",
    description="ガントチャート表示用にフィルタ付きでチケット一覧を返す。最大 500 件。ページネーションなし。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def get_gantt_tickets(
    request: Request,
    project_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    status: TicketStatus | None = Query(default=None),
    tracker: TicketTracker | None = Query(default=None),
    priority: TicketPriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
    service: GanttTicketService = Depends(_get_service),
) -> GanttTicketListResponse:
    """ガントチャート表示用チケット一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.gantt.request",
        user_id=user.id,
        project_id=project_id,
        product_id=product_id,
        status=status,
        tracker=tracker,
        request_id=request_id,
    )

    query = GanttTicketQuery(
        project_id=project_id,
        product_id=product_id,
        status=status,
        tracker=tracker,
        priority=priority,
        assignee_id=assignee_id,
    )

    result = await service.get_gantt_list(query, user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value
