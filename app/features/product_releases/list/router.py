"""製品作業サイクル Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Repository 層に委譲する（集計なし・薄い Service は省略）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.clock import Clock, get_clock
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.product_releases.list.repository import ProductReleaseRepository
from app.features.product_releases.list.schemas import (
    ProductReleaseCreateRequest,
    ProductReleaseItem,
    ProductReleaseListResponse,
    ProductReleaseUpdateRequest,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="product_releases")

router = APIRouter(prefix="/api/v1/product-releases", tags=["product-releases"])


def _get_repository(
    session: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> ProductReleaseRepository:
    """依存性注入: DB セッション + Clock を受け取り Repository を構築して返す。"""
    return ProductReleaseRepository(session, clock)


@router.get(
    "",
    response_model=ProductReleaseListResponse,
    summary="製品作業サイクル一覧取得",
    description="product_id を指定するとその製品のサイクルのみ返す。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_product_releases(
    request: Request,
    product_id: int | None = Query(default=None, description="製品 ID で絞り込み"),
    user: AuthenticatedUser = Depends(get_current_user),
    repository: ProductReleaseRepository = Depends(_get_repository),
) -> ProductReleaseListResponse:
    """製品作業サイクル一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "product_releases.list.request",
        user_id=user.id,
        product_id=product_id,
        request_id=request_id,
    )

    result = await repository.get_list(product_id=product_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "product_releases.list.response",
        user_id=user.id,
        total=result.value.total,
        request_id=request_id,
    )
    return result.value


@router.post(
    "",
    response_model=ProductReleaseItem,
    status_code=201,
    summary="製品作業サイクル作成",
    description="新しい作業サイクル（初回リリース・仕様変更・バージョンアップ等）を作成する。",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def create_product_release(
    request: Request,
    body: ProductReleaseCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: ProductReleaseRepository = Depends(_get_repository),
) -> ProductReleaseItem:
    """製品作業サイクルを作成する。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "product_releases.create.request",
        user_id=user.id,
        product_id=body.product_id,
        release_type=body.release_type,
        request_id=request_id,
    )

    result = await repository.create(req=body, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "product_releases.create.success",
        user_id=user.id,
        release_id=result.value.id,
        request_id=request_id,
    )
    return result.value


@router.patch(
    "/{release_id}",
    response_model=ProductReleaseItem,
    summary="製品作業サイクル更新",
    description="作業サイクルの名称・種別・進捗・目標日を更新する。",
    dependencies=[permission_required(Actions.UPDATE, Resources.TASK)],
)
async def update_product_release(
    release_id: int,
    request: Request,
    body: ProductReleaseUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: ProductReleaseRepository = Depends(_get_repository),
) -> ProductReleaseItem:
    """製品作業サイクルを更新する。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "product_releases.update.request",
        user_id=user.id,
        release_id=release_id,
        request_id=request_id,
    )

    result = await repository.update(release_id=release_id, req=body, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "product_releases.update.success",
        user_id=user.id,
        release_id=result.value.id,
        request_id=request_id,
    )
    return result.value
