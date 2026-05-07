"""チケット承認 Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
業務制約:
  - pending の承認が存在する間は当該チケットの status=in_progress 以降への遷移をブロック
  - 四眼原則: requester_id != approver_id（Service 層で validate_four_eyes_principle を呼ぶ）
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.common.state_machine import validate_transition
from app.common.validators import validate_four_eyes_principle
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.approval.schemas import (
    ApprovalActorResponse,
    ApprovalListResponse,
    ApprovalResponse,
    CreateApprovalRequest,
    ReviewApprovalRequest,
)
from app.models.approval import TicketApprovalOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="tickets.approval.repository")

# 承認ステータスの遷移マップ（validate_transition で使用）
# pending のみが遷移可能。approved / rejected は終端状態
_APPROVAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"approved", "rejected"}),
    "approved": frozenset(),
    "rejected": frozenset(),
}


def _to_response(row: TicketApprovalOrm) -> ApprovalResponse:
    """ORM → Pydantic レスポンス変換。try スコープ内で呼ぶこと（変換例外を捕捉するため）。"""
    return ApprovalResponse(
        id=row.id,
        ticket_id=row.ticket_id,
        title=row.title,
        status=row.status,  # type: ignore[arg-type]
        requester=ApprovalActorResponse(
            id=row.requester.id,
            display_name=row.requester.display_name,
        ),
        approver=(
            ApprovalActorResponse(id=row.approver.id, display_name=row.approver.display_name)
            if row.approver is not None
            else None
        ),
        comment=row.comment,
        created_at=row.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        updated_at=row.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


class TicketApprovalRepository:
    """チケット承認のデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()

    async def list_by_ticket(
        self,
        ticket_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[ApprovalListResponse]:
        """チケットに紐づく承認一覧を返す（delete_flg == 0 のみ）。"""
        try:
            stmt = (
                select(TicketApprovalOrm)
                .options(
                    joinedload(TicketApprovalOrm.requester),
                    joinedload(TicketApprovalOrm.approver),
                )
                .where(
                    TicketApprovalOrm.ticket_id == ticket_id,
                    TicketApprovalOrm.delete_flg == 0,
                )
                .order_by(TicketApprovalOrm.created_at)
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()
            items = [_to_response(r) for r in rows]
            return Ok(ApprovalListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("tickets.approval.list.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="承認一覧の取得に失敗しました", details=exc))

    async def create(
        self,
        ticket_id: int,
        req: CreateApprovalRequest,
        requester_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[ApprovalResponse]:
        """チケットに承認申請を作成する（status=pending）。"""
        try:
            # チケット存在確認
            ticket = await self._session.get(TicketOrm, ticket_id)
            if ticket is None or ticket.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"チケット ID={ticket_id} が見つかりません"))

            now = self._clock.now()
            approval = TicketApprovalOrm(
                ticket_id=ticket_id,
                requester_id=requester_id,
                approver_id=None,
                status="pending",
                title=req.title,
                comment=None,
                delete_flg=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(approval)
            await self._session.flush()

            # N+1 回避: requester を joinedload で再取得
            stmt = (
                select(TicketApprovalOrm)
                .options(
                    joinedload(TicketApprovalOrm.requester),
                    joinedload(TicketApprovalOrm.approver),
                )
                .where(TicketApprovalOrm.id == approval.id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()
            response = _to_response(row)
            await self._session.commit()
            logger.info("tickets.approval.created", ticket_id=ticket_id, approval_id=approval.id)
            return Ok(response)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.approval.create.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="承認申請の作成に失敗しました", details=exc))

    async def review(
        self,
        ticket_id: int,
        approval_id: int,
        req: ReviewApprovalRequest,
        approver_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[ApprovalResponse]:
        """承認または却下を実行する。

        状態遷移: pending → approved / rejected
        四眼原則: approval.requester_id != approver_id を Repository 内で検証する。
        """
        try:
            approval = await self._session.get(TicketApprovalOrm, approval_id)
            if approval is None or approval.delete_flg != 0 or approval.ticket_id != ticket_id:
                return Err(AppError(type="NOT_FOUND", message=f"承認 ID={approval_id} が見つかりません"))

            # 業務上絶対条件 #2 + #3: 四眼原則（申請者 ≠ 承認者）の機械的担保
            four_eyes = validate_four_eyes_principle(
                requester_id=str(approval.requester_id),
                approver_id=str(approver_id),
            )
            if not four_eyes.ok:
                return four_eyes  # type: ignore[return-value]

            new_status = "approved" if req.action == "approve" else "rejected"
            if not validate_transition(approval.status, new_status, _APPROVAL_TRANSITIONS):
                return Err(AppError(
                    type="BUSINESS_RULE",
                    message=f"承認ステータス '{approval.status}' から '{new_status}' への遷移は許可されていません",
                ))

            now = self._clock.now()
            approval.status = new_status
            approval.approver_id = approver_id
            approval.comment = req.comment
            approval.updated_at = now
            await self._session.flush()

            stmt = (
                select(TicketApprovalOrm)
                .options(
                    joinedload(TicketApprovalOrm.requester),
                    joinedload(TicketApprovalOrm.approver),
                )
                .where(TicketApprovalOrm.id == approval_id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()
            response = _to_response(row)
            await self._session.commit()
            logger.info(
                "tickets.approval.reviewed",
                ticket_id=ticket_id,
                approval_id=approval_id,
                action=req.action,
            )
            return Ok(response)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.approval.review.error", approval_id=approval_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="承認操作に失敗しました", details=exc))

    async def has_pending(self, ticket_id: int) -> bool:
        """チケットに pending 承認が存在するかを返す。

        TicketUpdateRepository からステータス遷移ガードとして呼ばれる。
        """
        stmt = (
            select(TicketApprovalOrm.id)
            .where(
                TicketApprovalOrm.ticket_id == ticket_id,
                TicketApprovalOrm.status == "pending",
                TicketApprovalOrm.delete_flg == 0,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
