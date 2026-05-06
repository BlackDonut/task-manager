"""チケット一覧 Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
仕様ソース: docs/ 未定義（初期実装）
画面: SCR-T001（チケット一覧）
業務制約:
  - delete_flg == 0 フィルタは筆略禁止（論理削除 L1）
  - N+1 クエリ禁止: product / assignee を joinedload、前後関係を selectinload で一括取得
# TODO(domain): インデックス設計は DB 設計書確定後に見直すこと
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.list.schemas import (
    AssigneeResponse,
    ProductResponse,
    TicketListQuery,
    TicketListResponse,
    TicketResponse,
)
from app.models.product import ProductOrm
from app.models.ticket import TicketDependencyOrm, TicketOrm  # noqa: F401 — TicketDependencyOrm をインポートしてメタデータに登録する

logger = get_logger(component="tickets.list.repository")


def _to_ticket_response(t: TicketOrm) -> TicketResponse:
    """ORM モデル → レスポンス Pydantic モデルに変換する。"""
    return TicketResponse(
        id=t.id,
        product=ProductResponse(id=t.product.id, name=t.product.name),
        parent_id=t.parent_id,
        tracker=t.tracker,  # type: ignore[arg-type]
        status=t.status,  # type: ignore[arg-type]
        priority=t.priority,  # type: ignore[arg-type]
        subject=t.subject,
        assignee=(
            AssigneeResponse(id=t.assignee.id, display_name=t.assignee.display_name)
            if t.assignee is not None
            else None
        ),
        due_date=t.due_date.isoformat() if t.due_date is not None else None,
        updated_at=t.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        done_ratio=t.done_ratio,
        depth=t.depth,
        predecessor_ids=[dep.predecessor_id for dep in t.dependencies_as_successor],
    )


class TicketListRepository:
    """チケット一覧のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_list(
        self,
        query: TicketListQuery,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時にスコープフィルタで使用
    ) -> Result[TicketListResponse]:
        """フィルタ・ページネーションを適用してチケット一覧を返す。

        N+1 回避: product / assignee を joinedload、前後関係を selectinload で一括取得する。
        delete_flg == 0 フィルタは筆略禁止（論理削除 L1）。

        Args:
            query: フィルタ条件（project_id / product_id / status 等）とページネーション設定
            scope: 組織スコープ（将来のマルチテナント対応時に使用）

        Returns:
            Ok(TicketListResponse): フィルタ後チケット一覧と総件数・ページ情報
            Err(AppError): DB アクセス失敗時
        """
        try:
            # --- フィルタ条件構築 ---
            base_where = [TicketOrm.delete_flg == 0]

            if query.project_id is not None:
                # プロジェクト経由で製品を絞り込む（サブクエリで N+1 回避）
                product_ids = select(ProductOrm.id).where(
                    ProductOrm.project_id == query.project_id,
                    ProductOrm.delete_flg == 0,
                )
                base_where.append(TicketOrm.product_id.in_(product_ids))
            if query.product_id is not None:
                base_where.append(TicketOrm.product_id == query.product_id)
            if query.status is not None:
                base_where.append(TicketOrm.status == query.status)
            if query.priority is not None:
                base_where.append(TicketOrm.priority == query.priority)
            if query.tracker is not None:
                base_where.append(TicketOrm.tracker == query.tracker)
            if query.assignee_id is not None:
                base_where.append(TicketOrm.assignee_id == query.assignee_id)
            if query.keyword is not None:
                base_where.append(TicketOrm.subject.contains(query.keyword))

            # --- 件数取得（join なしで高速化） ---
            count_stmt = select(func.count()).select_from(TicketOrm).where(*base_where)
            total: int = (await self._session.scalar(count_stmt)) or 0
            total_pages = max(1, (total + query.page_size - 1) // query.page_size)

            # --- データ取得（joinedload で N+1 回避） ---
            data_stmt = (
                select(TicketOrm)
                .options(
                    joinedload(TicketOrm.product),
                    joinedload(TicketOrm.assignee),
                    # 前後関係: selectinload でまとめて取得（joinedload は Collection に非推奨）
                    selectinload(TicketOrm.dependencies_as_successor),
                )
                .where(*base_where)
                # 製品グループ表示のため product_id 昇順を第1キーにして同一製品チケットを連続させる。
                # 製品内は更新日時降順で最新チケットを先頭に表示する。
                .order_by(TicketOrm.product_id.asc(), TicketOrm.updated_at.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
            )
            rows = (await self._session.execute(data_stmt)).unique().scalars().all()

            # --- レスポンス変換（try スコープ内で変換例外も捕捉） ---
            items = [_to_ticket_response(t) for t in rows]

            return Ok(
                TicketListResponse(
                    items=items,
                    total=total,
                    page=query.page,
                    page_size=query.page_size,
                    total_pages=total_pages,
                )
            )
        except Exception as exc:
            logger.error("tickets.list.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="チケット一覧の取得に失敗しました", details=exc))
