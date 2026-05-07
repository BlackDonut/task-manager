"""フェーズ進捗マトリクス Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
# TODO(domain): インデックス設計は DB 設計書確定後に見直すこと
"""

from __future__ import annotations

import datetime
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import Clock
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.list.schemas import ProductResponse
from app.features.tickets.matrix.schemas import (
    PhaseCell,
    PhaseMatrixQuery,
    PhaseMatrixResponse,
    PhaseState,
    ProductPhaseRow,
)
from app.models.product import ProductOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="tickets.matrix.repository")

# 完了扱いのステータス
_DONE_STATUSES: frozenset[str] = frozenset(("resolved", "closed"))

# 却下ステータス
_REJECTED_STATUS = "rejected"


def _classify_state(status: str, due_date: datetime.date | None, today: datetime.date) -> PhaseState:
    """チケットのステータスと期日からセルの状態を分類する。

    優先順位: completed > rejected > overdue > in_progress > not_started
    """
    if status in _DONE_STATUSES:
        return PhaseState.completed
    if status == _REJECTED_STATUS:
        return PhaseState.rejected
    # 期限超過判定（due_date あり・今日より前）
    if due_date is not None and due_date < today:
        return PhaseState.overdue
    if status == "in_progress":
        return PhaseState.in_progress
    # status == "new" またはその他
    return PhaseState.not_started


class PhaseMatrixRepository:
    """フェーズ進捗マトリクス用データアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def get_phase_matrix(
        self,
        query: PhaseMatrixQuery,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時にスコープフィルタで使用
    ) -> Result[PhaseMatrixResponse]:
        """製品×フェーズのマトリクスデータを返す。

        N+1 回避: 製品とフェーズチケットをそれぞれ一括取得し、アプリ層でクロスジョインする。
        delete_flg == 0 フィルタは省略禁止（論理削除 L1）。
        """
        try:
            today: datetime.date = self._clock.now().date()

            # --- 1. 製品一覧取得 ---
            product_where = [ProductOrm.delete_flg == 0]
            if query.project_id is not None:
                product_where.append(ProductOrm.project_id == query.project_id)

            product_stmt = (
                select(ProductOrm)
                .where(*product_where)
                .order_by(ProductOrm.id)
            )
            product_rows = (await self._session.execute(product_stmt)).scalars().all()

            if not product_rows:
                return Ok(PhaseMatrixResponse(phases=[], rows=[]))

            product_ids = [p.id for p in product_rows]

            # --- 2. フェーズチケット一括取得 ---
            # 同一製品・同一フェーズ名で複数チケットが存在する場合は id 昇順で先頭 1 件を使用する
            ticket_stmt = (
                select(TicketOrm)
                .where(
                    TicketOrm.delete_flg == 0,
                    TicketOrm.tracker == "phase",
                    TicketOrm.product_id.in_(product_ids),
                )
                .order_by(TicketOrm.subject, TicketOrm.id)
            )
            ticket_rows = (await self._session.execute(ticket_stmt)).scalars().all()

            # --- 3. 列（フェーズ名）の収集・昇順ソート ---
            # 同一フェーズ名が複数製品にまたがる場合でも列は 1 本のみ
            seen_subjects: set[str] = set()
            phase_subjects: list[str] = []
            for t in ticket_rows:
                if t.subject not in seen_subjects:
                    phase_subjects.append(t.subject)
                    seen_subjects.add(t.subject)
            phase_subjects.sort()

            # --- 4. 製品 × フェーズ マッピング構築 ---
            # {product_id: {phase_subject: TicketOrm}}
            # 同名フェーズが複数存在する場合は id 昇順で先頭 1 件を使用（ticket_stmt の order_by で保証）
            phase_map: dict[int, dict[str, TicketOrm]] = defaultdict(dict)
            for t in ticket_rows:
                if t.subject not in phase_map[t.product_id]:
                    phase_map[t.product_id][t.subject] = t

            # --- 5. マトリクス行の構築 ---
            rows: list[ProductPhaseRow] = []
            for product in product_rows:
                cells: list[PhaseCell] = []
                for subject in phase_subjects:
                    ticket = phase_map[product.id].get(subject)
                    if ticket is None:
                        cells.append(
                            PhaseCell(
                                phase_subject=subject,
                                ticket_id=None,
                                status=None,
                                due_date=None,
                                state=PhaseState.none,
                            )
                        )
                    else:
                        state = _classify_state(ticket.status, ticket.due_date, today)
                        cells.append(
                            PhaseCell(
                                phase_subject=subject,
                                ticket_id=ticket.id,
                                status=ticket.status,
                                due_date=ticket.due_date.isoformat() if ticket.due_date else None,
                                state=state,
                            )
                        )
                rows.append(
                    ProductPhaseRow(
                        product=ProductResponse(id=product.id, name=product.name),
                        cells=cells,
                    )
                )

            logger.info(
                "tickets.matrix.repository.success",
                phases_count=len(phase_subjects),
                products_count=len(rows),
            )
            return Ok(PhaseMatrixResponse(phases=phase_subjects, rows=rows))

        except Exception as exc:
            logger.error("tickets.matrix.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="フェーズ進捗マトリクスの取得に失敗しました", details=exc))
