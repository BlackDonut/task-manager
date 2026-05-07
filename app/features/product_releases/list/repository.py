"""製品作業サイクル Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
画面: SCR-T001（チケット一覧 リリースタブ切り替え）
業務制約:
  - delete_flg == 0 フィルタは省略禁止（論理削除 L1）
  - N+1 回避: product を joinedload で一括取得
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import Clock, SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.product_releases.list.schemas import (
    ProductReleaseCreateRequest,
    ProductReleaseItem,
    ProductReleaseListResponse,
    ProductReleaseUpdateRequest,
)
from app.models.product import ProductOrm, ProductReleaseOrm

logger = get_logger(component="product_releases.repository")


def _to_item(r: ProductReleaseOrm) -> ProductReleaseItem:
    """ORM → Pydantic 変換。"""
    return ProductReleaseItem(
        id=r.id,
        product_id=r.product_id,
        name=r.name,
        release_type=r.release_type,
        status=r.status,
        target_date=r.target_date,
    )


class ProductReleaseRepository:
    """製品作業サイクルのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or SystemClock()

    async def get_list(
        self,
        product_id: int | None,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時に使用
    ) -> Result[ProductReleaseListResponse]:
        """製品 ID でフィルタしたサイクル一覧を返す。

        Args:
            product_id: 絞り込む製品 ID。None の場合は全製品のサイクルを返す。
            scope: 組織スコープ（将来のマルチテナント対応時に使用）

        Returns:
            Ok(ProductReleaseListResponse)
            Err(AppError): DB アクセス失敗時
        """
        try:
            base_where = [ProductReleaseOrm.delete_flg == 0]
            if product_id is not None:
                # 製品 ID でフィルタ
                base_where.append(ProductReleaseOrm.product_id == product_id)

            stmt = (
                select(ProductReleaseOrm)
                .where(*base_where)
                .order_by(ProductReleaseOrm.created_at.asc())
            )
            rows = (await self._session.execute(stmt)).scalars().all()
            items = [_to_item(r) for r in rows]
        except Exception as exc:
            logger.error("product_releases.list.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(ProductReleaseListResponse(items=items, total=len(items)))

    async def create(
        self,
        req: ProductReleaseCreateRequest,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[ProductReleaseItem]:
        """製品作業サイクルを新規作成する。

        Args:
            req: 作成リクエスト
            scope: 組織スコープ

        Returns:
            Ok(ProductReleaseItem): 作成されたリリース
            Err(AppError): 製品が存在しない / DB エラー
        """
        try:
            # 製品の存在確認（論理削除済みも除外）
            product_exists = (
                await self._session.execute(
                    select(ProductOrm.id).where(
                        ProductOrm.id == req.product_id,
                        ProductOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if product_exists is None:
                return Err(AppError(type="NOT_FOUND", message="指定された製品が見つかりません"))

            now = self._clock.now().replace(tzinfo=None)  # DB は naive datetime で格納
            release = ProductReleaseOrm(
                product_id=req.product_id,
                name=req.name,
                release_type=req.release_type,
                status=req.status,
                target_date=req.target_date,
                delete_flg=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(release)
            await self._session.flush()
            await self._session.refresh(release)
        except Exception as exc:
            logger.error("product_releases.create.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        logger.info("product_releases.create.success", release_id=release.id, product_id=release.product_id)
        return Ok(_to_item(release))

    async def update(
        self,
        release_id: int,
        req: ProductReleaseUpdateRequest,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[ProductReleaseItem]:
        """製品作業サイクルを更新する。

        Args:
            release_id: 更新対象のリリース ID
            req: 更新リクエスト
            scope: 組織スコープ

        Returns:
            Ok(ProductReleaseItem): 更新後のリリース
            Err(AppError): 存在しない / DB エラー
        """
        try:
            release = (
                await self._session.execute(
                    select(ProductReleaseOrm).where(
                        ProductReleaseOrm.id == release_id,
                        ProductReleaseOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if release is None:
                return Err(AppError(type="NOT_FOUND", message="指定された作業サイクルが見つかりません"))

            release.name = req.name
            release.release_type = req.release_type
            release.status = req.status
            release.target_date = req.target_date
            release.updated_at = self._clock.now().replace(tzinfo=None)
            await self._session.flush()
            await self._session.refresh(release)
        except Exception as exc:
            logger.error("product_releases.update.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        logger.info("product_releases.update.success", release_id=release.id)
        return Ok(_to_item(release))
