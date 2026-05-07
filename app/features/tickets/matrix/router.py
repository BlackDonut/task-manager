"""フェーズ進捗マトリクス Router。

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
from app.features.tickets.matrix.repository import PhaseMatrixRepository
from app.features.tickets.matrix.schemas import PhaseMatrixQuery, PhaseMatrixResponse
from app.features.tickets.matrix.service import PhaseMatrixService

logger = get_logger(component="tickets.matrix")

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _get_service(session: AsyncSession = Depends(get_db)) -> PhaseMatrixService:
    """依存性注入: DB セッションを受け取り PhaseMatrixService を構築して返す。"""
    return PhaseMatrixService(PhaseMatrixRepository(session, SystemClock()))


@router.get(
    "/phase-matrix",
    response_model=PhaseMatrixResponse,
    summary="フェーズ進捗マトリクス取得",
    description=(
        "製品×フェーズのクロス集計マトリクスを返す。"
        "フェーズゲート確認（全製品の全フェーズ完了状態を俯瞰）専用エンドポイント。"
        "SCR005 フェーズマトリクス画面専用。"
    ),
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def get_phase_matrix(
    request: Request,
    project_id: int | None = Query(default=None, description="プロジェクト ID でフィルタ"),
    user: AuthenticatedUser = Depends(get_current_user),
    service: PhaseMatrixService = Depends(_get_service),
) -> PhaseMatrixResponse:
    """製品×フェーズのマトリクスデータを返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "tickets.matrix.request",
        user_id=user.id,
        project_id=project_id,
        request_id=request_id,
    )

    query = PhaseMatrixQuery(project_id=project_id)
    result = await service.get_phase_matrix(query, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "tickets.matrix.response",
        user_id=user.id,
        phases_count=len(result.value.phases),
        products_count=len(result.value.rows),
        request_id=request_id,
    )
    return result.value
