"""製品一覧 Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Repository 層に委譲する（集計なし・薄い Service は省略）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.products.list.repository import ProductListRepository
from app.features.products.list.schemas import ProductListResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="products.list")

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def _get_repository(session: AsyncSession = Depends(get_db)) -> ProductListRepository:
    """依存性注入: DB セッションを受け取り ProductListRepository を構築して返す。"""
    return ProductListRepository(session)


@router.get(
    "",
    response_model=ProductListResponse,
    summary="製品一覧取得",
    description="チケットフィルタ用製品一覧を返す。project_id を指定するとそのプロジェクト配下のみ返す。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_products(
    request: Request,
    project_id: int | None = Query(default=None, description="プロジェクト ID で絞り込み"),
    user: AuthenticatedUser = Depends(get_current_user),
    repository: ProductListRepository = Depends(_get_repository),
) -> ProductListResponse:
    """製品一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "products.list.request",
        user_id=user.id,
        project_id=project_id,
        request_id=request_id,
    )

    result = await repository.get_list(project_id=project_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)

    logger.info(
        "products.list.response",
        user_id=user.id,
        total=result.value.total,
        request_id=request_id,
    )

    return result.value
