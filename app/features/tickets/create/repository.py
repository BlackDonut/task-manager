"""チケット作成 Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
仕様ソース: docs/ 未定義（初期実装）
画面: SCR-T001（チケット一覧 タスク追加ダイアログ）
業務制約:
  - delete_flg == 0 で新規レコードを作成する
  - depth は親チケットの depth + 1 で自動計算し、上限 _DEPTH_MAX を超えないよう制約する
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.create.schemas import TicketCreateRequest, TicketCreateResponse
from app.features.tickets.list.schemas import AssigneeResponse, ProductResponse
from app.models.ticket import TicketDependencyOrm, TicketOrm  # TicketDependencyOrm: 依存レコード作成・メタデータ登録

logger = get_logger(component="tickets.create.repository")

# 階層深度の上限（TicketOrm.depth のアプリ層制約と一致させること）
_DEPTH_MAX = 3


class TicketCreateRepository:
    """チケット作成のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        # Clock ファクトリ: テストでは FixedClock を注入して時刻依存ロジックを検証可能にする
        self._clock = clock if clock is not None else SystemClock()

    async def create(
        self,
        req: TicketCreateRequest,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時に使用
    ) -> Result[TicketCreateResponse]:
        """チケットを新規作成して作成済みレコードを返す。

        depth は親チケットの depth + 1 で自動計算する（最大 _DEPTH_MAX）。
        作成後に product / assignee を joinedload で再取得してレスポンスを構築する。

        Args:
            req: チケット作成リクエスト
            scope: 組織スコープ（将来のマルチテナント対応時に使用）

        Returns:
            Ok(TicketCreateResponse): 作成済みチケット
            Err(AppError): 親チケット未存在 / DB エラー時
        """
        try:
            # --- depth 計算: 親がある場合は parent.depth + 1、上限 _DEPTH_MAX ---
            depth = 0
            if req.parent_id is not None:
                parent = await self._session.get(TicketOrm, req.parent_id)
                if parent is None or parent.delete_flg != 0:
                    return Err(AppError(
                        type="NOT_FOUND",
                        message=f"親チケット ID={req.parent_id} が見つかりません",
                    ))
                depth = min(parent.depth + 1, _DEPTH_MAX)

            now = self._clock.now()

            ticket = TicketOrm(
                product_id=req.product_id,
                release_id=req.release_id,
                parent_id=req.parent_id,
                tracker=req.tracker,
                status=req.status,
                priority=req.priority,
                subject=req.subject,
                assignee_id=req.assignee_id,
                due_date=req.due_date,
                done_ratio=req.done_ratio,
                depth=depth,
                delete_flg=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(ticket)
            # flush で autoincrement id を確定させる（commit より前に id が必要）
            await self._session.flush()

            # --- 先行チケット（前後関係）の登録 ---
            # flush 後に ticket.id が確定しているため、ここで依存レコードを挿入する
            for pred_id in req.predecessor_ids:
                pred = await self._session.get(TicketOrm, pred_id)
                if pred is None or pred.delete_flg != 0:
                    # flush 後なので明示的ロールバックが必要
                    await self._session.rollback()
                    return Err(AppError(
                        type="NOT_FOUND",
                        message=f"先行チケット ID={pred_id} が見つかりません",
                    ))
                self._session.add(TicketDependencyOrm(predecessor_id=pred_id, successor_id=ticket.id))

            # --- N+1 回避: 作成直後のレコードを product / assignee 込みで再取得 ---
            stmt = (
                select(TicketOrm)
                .options(
                    joinedload(TicketOrm.product),
                    joinedload(TicketOrm.assignee),
                    selectinload(TicketOrm.dependencies_as_successor),
                )
                .where(TicketOrm.id == ticket.id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()

            # --- レスポンス変換（try スコープ内で変換例外も捕捉） ---
            response = TicketCreateResponse(
                id=row.id,
                subject=row.subject,
                product=ProductResponse(id=row.product.id, name=row.product.name),
                parent_id=row.parent_id,
                tracker=row.tracker,  # type: ignore[arg-type]
                status=row.status,  # type: ignore[arg-type]
                priority=row.priority,  # type: ignore[arg-type]
                done_ratio=row.done_ratio,
                depth=row.depth,
                due_date=row.due_date.isoformat() if row.due_date is not None else None,
                assignee=(
                    AssigneeResponse(id=row.assignee.id, display_name=row.assignee.display_name)
                    if row.assignee is not None
                    else None
                ),
                predecessor_ids=[dep.predecessor_id for dep in row.dependencies_as_successor],
                updated_at=row.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            await self._session.commit()
            logger.info("tickets.create.repository.created", ticket_id=row.id, product_id=row.product_id)
            return Ok(response)

        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.create.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="チケットの作成に失敗しました", details=exc))
