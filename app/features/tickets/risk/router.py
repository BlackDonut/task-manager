"""リスクダッシュボード Router。

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
from app.core.clock import SystemClock
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.risk.repository import RiskDashboardRepository
from app.features.tickets.risk.schemas import RiskDashboardQuery, RiskDashboardResponse
from app.features.tickets.risk.service import RiskDashboardService

logger = get_logger(component="tickets.risk")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> RiskDashboardService:
    """依存性注入: DB セッションを受け取り RiskDashboardService を構築して返す。"""
    return RiskDashboardService(RiskDashboardRepository(session, SystemClock()))


@router.get(
    "/risk-summary",
    response_model=RiskDashboardResponse,
    summary="リスクダッシュボード取得",
    description=(
        "遅延・期限直前・未割当チケットの集計と製品別進捗を返す。"
        "SCR003 リスクダッシュボード専用エンドポイント。"
    ),
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def get_risk_summary(
    request: Request,
    project_id: int | None = Query(default=None, description="プロジェクト ID でフィルタ"),
    user: AuthenticatedUser = Depends(get_current_user),
    service: RiskDashboardService = Depends(_get_service),
) -> RiskDashboardResponse:
    """リスクダッシュボードデータを返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.risk.request",
        user_id=user.id,
        project_id=project_id,
        request_id=request_id,
    )

    query = RiskDashboardQuery(project_id=project_id)

    result = await service.get_risk_dashboard(query, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "tickets.risk.response",
        user_id=user.id,
        overdue=result.value.summary.overdue_count,
        at_risk=result.value.summary.at_risk_count,
        request_id=request_id,
    )
    return result.value
