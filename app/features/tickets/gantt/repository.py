"""ガントチャート Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
# TODO(domain): インデックス設計は DB 設計書確定後に見直すこと
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.gantt.schemas import (
    GanttTicketListResponse,
    GanttTicketQuery,
    GanttTicketResponse,
)
from app.features.tickets.list.schemas import (
    AssigneeResponse,
    ProductResponse,
)
from app.models.product import ProductOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="tickets.gantt.repository")

# ガントチャートの最大取得件数。
# 全件表示のためページネーションなし。1000 件超で一括更新禁止 (L1) ではなく参照のみのため 500 件上限とする。
_GANTT_MAX_ITEMS = 500


def _to_gantt_response(t: TicketOrm) -> GanttTicketResponse:
    """ORM モデル → ガントチャートレスポンス Pydantic モデルに変換する。"""
    return GanttTicketResponse(
        id=t.id,
        subject=t.subject,
        product=ProductResponse(id=t.product.id, name=t.product.name),
        parent_id=t.parent_id,
        status=t.status,  # type: ignore[arg-type]
        priority=t.priority,  # type: ignore[arg-type]
        tracker=t.tracker,  # type: ignore[arg-type]
        done_ratio=t.done_ratio,
        start_date=t.created_at.strftime("%Y-%m-%d"),
        due_date=t.due_date.isoformat() if t.due_date is not None else None,
        assignee=(
            AssigneeResponse(id=t.assignee.id, display_name=t.assignee.display_name)
            if t.assignee is not None
            else None
        ),
    )


class GanttTicketRepository:
    """ガントチャート表示用チケットのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_gantt_list(
        self,
        query: GanttTicketQuery,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時にスコープフィルタで使用
    ) -> Result[GanttTicketListResponse]:
        """フィルタを適用してガントチャート用チケット一覧を返す。

        N+1 回避: product / assignee を joinedload で一括取得する。
        delete_flg == 0 フィルタは省略禁止（論理削除 L1）。
        最大 _GANTT_MAX_ITEMS 件まで返す（ページネーションなし）。
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

            # --- データ取得（joinedload で N+1 回避・作成日昇順） ---
            stmt = (
                select(TicketOrm)
                .options(
                    joinedload(TicketOrm.product),
                    joinedload(TicketOrm.assignee),
                )
                .where(*base_where)
                .order_by(TicketOrm.created_at.asc())
                .limit(_GANTT_MAX_ITEMS)
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()

            # --- レスポンス変換（try スコープ内で変換例外も捕捉） ---
            items = [_to_gantt_response(t) for t in rows]

            return Ok(GanttTicketListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("tickets.gantt.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="ガントチャートデータの取得に失敗しました", details=exc))
