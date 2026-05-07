"""チケット承認 Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.approval.repository import TicketApprovalRepository
from app.features.tickets.approval.schemas import (
    ApprovalListResponse,
    ApprovalResponse,
    CreateApprovalRequest,
    ReviewApprovalRequest,
)


class TicketApprovalService:
    """チケット承認ユースケース。"""

    def __init__(self, repository: TicketApprovalRepository) -> None:
        self._repository = repository

    async def list_approvals(
        self,
        ticket_id: int,
        scope: OrganizationScope,
    ) -> Result[ApprovalListResponse]:
        """チケットの承認一覧を返す。"""
        return await self._repository.list_by_ticket(ticket_id, scope)

    async def create_approval(
        self,
        ticket_id: int,
        req: CreateApprovalRequest,
        requester_id: int,
        scope: OrganizationScope,
    ) -> Result[ApprovalResponse]:
        """承認申請を作成する。"""
        return await self._repository.create(ticket_id, req, requester_id, scope)

    async def review_approval(
        self,
        ticket_id: int,
        approval_id: int,
        req: ReviewApprovalRequest,
        approver_id: int,
        scope: OrganizationScope,
    ) -> Result[ApprovalResponse]:
        """承認または却下を実行する。

        四眼原則: Repository 内で approval.requester_id != approver_id を検証する。
        """
        return await self._repository.review(ticket_id, approval_id, req, approver_id, scope)
