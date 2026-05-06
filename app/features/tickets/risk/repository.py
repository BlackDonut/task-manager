"""リスクダッシュボード Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
# TODO(domain): インデックス設計は DB 設計書確定後に見直すこと
"""

from __future__ import annotations

import datetime

from sqlalchemy import case, cast, func, select
from sqlalchemy import Integer as SAInteger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import Clock
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.list.schemas import AssigneeResponse, ProductResponse
from app.features.tickets.risk.schemas import (
    ProductRiskSummary,
    RiskDashboardQuery,
    RiskDashboardResponse,
    RiskSummary,
    RiskTicketResponse,
)
from app.models.product import ProductOrm
from app.models.ticket import TicketDependencyOrm, TicketOrm  # noqa: F401 — TicketDependencyOrm をインポートしてメタデータに登録する
from app.models.user import UserOrm

logger = get_logger(component="tickets.risk.repository")

# 期限超過・リスクチケットの最大取得件数
_RISK_MAX_ITEMS = 200

# 完了扱いのステータス（これらは遅延カウントから除外する）
_DONE_STATUSES = ("resolved", "closed", "rejected")


def _build_product_scope_subquery(project_id: int | None) -> list:
    """project_id が指定された場合の製品スコープフィルタ条件を返す。"""
    if project_id is None:
        return []
    product_ids = select(ProductOrm.id).where(
        ProductOrm.project_id == project_id,
        ProductOrm.delete_flg == 0,
    )
    return [TicketOrm.product_id.in_(product_ids)]


class RiskDashboardRepository:
    """リスクダッシュボード用チケット集計のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def get_risk_dashboard(
        self,
        query: RiskDashboardQuery,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時にスコープフィルタで使用
    ) -> Result[RiskDashboardResponse]:
        """遅延・リスクチケットの集計とリストを返す。

        N+1 回避: product / assignee を joinedload で一括取得する。
        delete_flg == 0 フィルタは省略禁止（論理削除 L1）。
        """
        try:
            # 現在日付（UTC→ローカルは要件確定後に調整）
            today: datetime.date = self._clock.now().date()
            at_risk_threshold: datetime.date = today + datetime.timedelta(days=3)

            scope_filter = _build_product_scope_subquery(query.project_id)
            base_where = [TicketOrm.delete_flg == 0, *scope_filter]
            active_where = [
                *base_where,
                TicketOrm.status.not_in(_DONE_STATUSES),
            ]

            # ----------------------------------------------------------------
            # 1. サマリー集計（スカラークエリ × 4 を並行発行）
            # ----------------------------------------------------------------

            overdue_stmt = (
                select(func.count())
                .select_from(TicketOrm)
                .where(
                    *active_where,
                    TicketOrm.due_date.isnot(None),
                    TicketOrm.due_date < today,
                )
            )
            at_risk_stmt = (
                select(func.count())
                .select_from(TicketOrm)
                .where(
                    *active_where,
                    TicketOrm.due_date.isnot(None),
                    TicketOrm.due_date >= today,
                    TicketOrm.due_date <= at_risk_threshold,
                )
            )
            unassigned_stmt = (
                select(func.count())
                .select_from(TicketOrm)
                .where(
                    *active_where,
                    TicketOrm.assignee_id.is_(None),
                )
            )
            in_progress_stmt = (
                select(func.count())
                .select_from(TicketOrm)
                .where(*active_where)
            )

            overdue_count = (await self._session.scalar(overdue_stmt)) or 0
            at_risk_count = (await self._session.scalar(at_risk_stmt)) or 0
            unassigned_count = (await self._session.scalar(unassigned_stmt)) or 0
            in_progress_count = (await self._session.scalar(in_progress_stmt)) or 0

            summary = RiskSummary(
                overdue_count=overdue_count,
                at_risk_count=at_risk_count,
                unassigned_count=unassigned_count,
                in_progress_count=in_progress_count,
            )

            # ----------------------------------------------------------------
            # 2. 製品別進捗・遅延集計
            #    GROUP BY products.id でまとめて取得し N+1 を回避する
            # ----------------------------------------------------------------

            # overdue_case: 未完了かつ due_date < today なら 1 それ以外 0
            overdue_case = case(
                (
                    (TicketOrm.status.not_in(_DONE_STATUSES))
                    & (TicketOrm.due_date.isnot(None))
                    & (TicketOrm.due_date < today),
                    1,
                ),
                else_=0,
            )

            product_agg_stmt = (
                select(
                    ProductOrm.id.label("product_id"),
                    ProductOrm.name.label("product_name"),
                    func.count(TicketOrm.id).label("total_count"),
                    # func.avg は FLOAT を返すため INTEGER にキャストして % 表示に合わせる
                    cast(func.avg(TicketOrm.done_ratio), SAInteger).label("avg_progress"),
                    func.sum(overdue_case).label("overdue_count"),
                )
                .join(TicketOrm, TicketOrm.product_id == ProductOrm.id)
                .where(*base_where)
                .group_by(ProductOrm.id, ProductOrm.name)
                .order_by(func.sum(overdue_case).desc(), ProductOrm.id.asc())
            )

            agg_rows = (await self._session.execute(product_agg_stmt)).all()

            product_summaries = [
                ProductRiskSummary(
                    product=ProductResponse(id=row.product_id, name=row.product_name),
                    total_count=row.total_count,
                    avg_progress=int(row.avg_progress or 0),
                    overdue_count=int(row.overdue_count or 0),
                )
                for row in agg_rows
            ]

            # ----------------------------------------------------------------
            # 3. リスクチケット一覧（遅延中 + 期限 3 日以内、最大 200 件）
            #    期日昇順（超過が先頭・未割当を優先するため NULLs LAST の代替として
            #    CASE WHEN assignee_id IS NULL THEN 0 ELSE 1 END を第2キーに使用）
            # ----------------------------------------------------------------

            risk_where = [
                *active_where,
                TicketOrm.due_date.isnot(None),
                TicketOrm.due_date <= at_risk_threshold,
            ]

            risk_stmt = (
                select(TicketOrm)
                .options(
                    joinedload(TicketOrm.product),
                    joinedload(TicketOrm.assignee),
                    # 前後関係: selectinload でまとめて取得
                    selectinload(TicketOrm.dependencies_as_successor),
                )
                .where(*risk_where)
                .order_by(
                    TicketOrm.due_date.asc(),
                    # 未割当を同一期日内で先頭に表示（0=未割当, 1=割当済み）
                    case((TicketOrm.assignee_id.is_(None), 0), else_=1).asc(),
                )
                .limit(_RISK_MAX_ITEMS)
            )

            risk_rows = (await self._session.execute(risk_stmt)).unique().scalars().all()

            risk_tickets = [
                RiskTicketResponse(
                    id=t.id,
                    subject=t.subject,
                    product=ProductResponse(id=t.product.id, name=t.product.name),
                    status=t.status,  # type: ignore[arg-type]
                    priority=t.priority,  # type: ignore[arg-type]
                    tracker=t.tracker,  # type: ignore[arg-type]
                    due_date=t.due_date.isoformat() if t.due_date is not None else None,
                    overdue_days=(today - t.due_date).days if t.due_date is not None else 0,
                    assignee=(
                        AssigneeResponse(id=t.assignee.id, display_name=t.assignee.display_name)
                        if t.assignee is not None
                        else None
                    ),
                    done_ratio=t.done_ratio,
                    predecessor_ids=[dep.predecessor_id for dep in t.dependencies_as_successor],
                )
                for t in risk_rows
            ]

            return Ok(
                RiskDashboardResponse(
                    summary=summary,
                    product_summaries=product_summaries,
                    risk_tickets=risk_tickets,
                )
            )
        except Exception as exc:
            logger.error("tickets.risk.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="リスクダッシュボードデータの取得に失敗しました", details=exc))
