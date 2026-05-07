"""チケット一覧 Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Service 層に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.list.repository import TicketListRepository
from app.features.tickets.list.schemas import TicketListQuery, TicketListResponse
from app.features.tickets.list.service import TicketListService
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="tickets.list")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> TicketListService:
    """依存性注入: DB セッションを受け取り TicketListService を構築して返す。"""
    return TicketListService(TicketListRepository(session))


@router.get(
    "",
    response_model=TicketListResponse,
    summary="チケット一覧取得",
    description="フィルタ・ページネーション付きでチケット一覧を返す。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_tickets(
    request: Request,
    project_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    release_id: int | None = Query(default=None, description="作業サイクル ID でフィルタ"),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    tracker: str | None = Query(default=None),
    assignee_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketListService = Depends(_get_service),
) -> TicketListResponse:
    """チケット一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.list.request",
        user_id=user.id,
        project_id=project_id,
        product_id=product_id,
        status=status,
        page=page,
        page_size=page_size,
        request_id=request_id,
    )

    query = TicketListQuery(
        project_id=project_id,
        product_id=product_id,
        release_id=release_id,
        status=status,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        tracker=tracker,  # type: ignore[arg-type]
        assignee_id=assignee_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    result = await service.get_list(query, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "tickets.list.response",
        user_id=user.id,
        total=result.value.total,
        request_id=request_id,
    )
    return result.value
