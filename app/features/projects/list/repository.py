"""プロジェクト一覧 Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.result import AppError, Err, Ok, Result
from app.features.projects.list.schemas import ProjectItem, ProjectListResponse
from app.models.project import ProjectOrm

logger = get_logger(component="projects.list.repository")


class ProjectListRepository:
    """プロジェクト一覧のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_list(
        self,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時にスコープフィルタで使用
    ) -> Result[ProjectListResponse]:
        """delete_flg == 0 の全プロジェクトを返す。

        delete_flg == 0 フィルタは省略禁止（論理削除 L1）。
        """
        try:
            stmt = (
                select(ProjectOrm)
                .where(ProjectOrm.delete_flg == 0)
                .order_by(ProjectOrm.name)
            )
            rows = (await self._session.execute(stmt)).scalars().all()

            # レスポンス変換（try スコープ内で変換例外も捕捉）
            items = [ProjectItem(id=p.id, name=p.name) for p in rows]

            return Ok(ProjectListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("projects.list.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="プロジェクト一覧の取得に失敗しました", details=exc))
