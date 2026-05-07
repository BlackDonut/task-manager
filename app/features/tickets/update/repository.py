"""チケット更新 Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
仕様ソース: docs/ 未定義（初期実装）
画面: SCR-T001（チケット一覧 編集ダイアログ）
業務制約:
  - delete_flg == 0 のチケットのみ更新可能
  - depth は親チケットの depth + 1 で自動再計算し、上限 _DEPTH_MAX を超えないよう制約する
  - predecessor_ids: 既存依存レコードを全削除してから再挿入する（差分更新は行わない）
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）
  - status が closed / resolved に変更された場合、同じタスクグループに属する未完了チケットを自動完了する
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.task_groups.list.repository import TaskGroupRepository
from app.features.tickets.list.schemas import AssigneeResponse, ProductResponse
from app.features.tickets.update.schemas import TicketUpdateRequest, TicketUpdateResponse
from app.models.approval import TicketApprovalOrm
from app.models.ticket import TicketDependencyOrm, TicketOrm

logger = get_logger(component="tickets.update.repository")

# 階層深度の上限（TicketOrm.depth のアプリ層制約と一致させること）
_DEPTH_MAX = 3


class TicketUpdateRepository:
    """チケット更新のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()

    async def update(
        self,
        ticket_id: int,
        req: TicketUpdateRequest,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時に使用
    ) -> Result[TicketUpdateResponse]:
        """チケットを更新して更新済みレコードを返す。

        predecessor_ids は既存依存レコードを全削除後に再挿入する。
        parent_id が変更された場合は depth を再計算する。

        Args:
            ticket_id: 更新対象チケット ID
            req: チケット更新リクエスト
            scope: 組織スコープ（将来のマルチテナント対応時に使用）

        Returns:
            Ok(TicketUpdateResponse): 更新済みチケット
            Err(AppError): チケット未存在 / 親チケット未存在 / 先行チケット未存在 / DB エラー時
        """
        try:
            # --- 対象チケット取得 ---
            ticket = await self._session.get(TicketOrm, ticket_id)
            if ticket is None or ticket.delete_flg != 0:
                return Err(AppError(
                    type="NOT_FOUND",
                    message=f"チケット ID={ticket_id} が見つかりません",
                ))

            # --- depth 再計算: parent_id が変わった場合のみ ---
            depth = ticket.depth
            if req.parent_id != ticket.parent_id:
                if req.parent_id is not None:
                    parent = await self._session.get(TicketOrm, req.parent_id)
                    if parent is None or parent.delete_flg != 0:
                        return Err(AppError(
                            type="NOT_FOUND",
                            message=f"親チケット ID={req.parent_id} が見つかりません",
                        ))
                    depth = min(parent.depth + 1, _DEPTH_MAX)
                else:
                    depth = 0

            # --- 承認ゲート: pending 承認が存在する場合は進行ステータスへの遷移をブロック ---
            # 業務上絶対条件 #2 「承認フローの完了確認」の機械的担保。
            # new/rejected 以外のステータスへの変更は pending 承認がない場合のみ許可する。
            _STATUS_REQUIRES_APPROVAL: frozenset[str] = frozenset({"in_progress", "resolved", "closed"})
            if req.status in _STATUS_REQUIRES_APPROVAL and req.status != ticket.status:
                pending_check = await self._session.execute(
                    select(TicketApprovalOrm.id)
                    .where(
                        TicketApprovalOrm.ticket_id == ticket_id,
                        TicketApprovalOrm.status == "pending",
                        TicketApprovalOrm.delete_flg == 0,
                    )
                    .limit(1)
                )
                if pending_check.scalar_one_or_none() is not None:
                    return Err(AppError(
                        type="BUSINESS_RULE",
                        message="未承認の承認申請が存在するため、ステータスを変更できません。先に承認を完了してください。",
                    ))

            # --- フィールド更新 ---
            ticket.tracker = req.tracker
            ticket.status = req.status
            ticket.priority = req.priority
            ticket.subject = req.subject
            ticket.release_id = req.release_id
            ticket.assignee_id = req.assignee_id
            ticket.due_date = req.due_date
            ticket.done_ratio = req.done_ratio
            ticket.parent_id = req.parent_id
            ticket.depth = depth
            ticket.updated_at = self._clock.now()

            # --- 先行チケット依存レコードの洗い替え ---
            await self._session.execute(
                delete(TicketDependencyOrm).where(TicketDependencyOrm.successor_id == ticket_id)
            )
            for pred_id in req.predecessor_ids:
                pred = await self._session.get(TicketOrm, pred_id)
                if pred is None or pred.delete_flg != 0:
                    await self._session.rollback()
                    return Err(AppError(
                        type="NOT_FOUND",
                        message=f"先行チケット ID={pred_id} が見つかりません",
                    ))
                self._session.add(TicketDependencyOrm(predecessor_id=pred_id, successor_id=ticket_id))

            await self._session.flush()

            # --- タスクグループ: 完了ステータスへの変更時に同グループ内の未完了チケットを自動完了 ---
            if req.status in ("closed", "resolved"):
                group_repo = TaskGroupRepository(self._session, self._clock)
                propagate_result = await group_repo.propagate_completion(
                    completed_ticket_id=ticket_id,
                    new_status=req.status,
                    scope=scope,
                )
                if propagate_result.is_err():
                    # 自動完了の失敗はログに記録するが、メインのチケット更新は続行する
                    logger.warning(
                        "tickets.update.propagate_completion.failed",
                        ticket_id=ticket_id,
                        error=str(propagate_result.unwrap_err()),
                    )

            # --- N+1 回避: 更新後のレコードを product / assignee 込みで再取得 ---
            stmt = (
                select(TicketOrm)
                .options(
                    joinedload(TicketOrm.product),
                    joinedload(TicketOrm.assignee),
                    selectinload(TicketOrm.dependencies_as_successor),
                )
                .where(TicketOrm.id == ticket_id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()

            # --- レスポンス変換（try スコープ内で変換例外も捕捉） ---
            response = TicketUpdateResponse(
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
            logger.info("tickets.update.repository.updated", ticket_id=row.id, product_id=row.product_id)
            return Ok(response)

        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.update.repository.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="チケットの更新に失敗しました", details=exc))
