"""プロジェクト一覧 Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Repository 層に委譲する（集計なし・薄い Service は省略）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.projects.list.repository import ProjectListRepository
from app.features.projects.list.schemas import ProjectListResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="projects.list")

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _get_repository(session: AsyncSession = Depends(get_db)) -> ProjectListRepository:
    """依存性注入: DB セッションを受け取り ProjectListRepository を構築して返す。"""
    return ProjectListRepository(session)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="プロジェクト一覧取得",
    description="チケットフィルタ用プロジェクト一覧を返す。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_projects(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: ProjectListRepository = Depends(_get_repository),
) -> ProjectListResponse:
    """プロジェクト一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "projects.list.request",
        user_id=user.id,
        request_id=request_id,
    )

    result = await repository.get_list(scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)

    logger.info(
        "projects.list.response",
        user_id=user.id,
        total=result.value.total,
        request_id=request_id,
    )
    return result.value
