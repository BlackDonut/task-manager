"""TicketApprovalService のユニットテスト。

テスト方針:
- Service は Repository の委譲のみ担うため、Repository をモックし Result 伝播を検証する
- DB アクセスは一切行わない（unittest.mock を使用）
- 認可チェック (permission_required) は Router 層のテスト対象のためここでは省略する
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.result import AppError, Err, Ok
from app.features.tickets.approval.schemas import (
    ApprovalListResponse,
    ApprovalResponse,
    CreateApprovalRequest,
    ReviewApprovalRequest,
)
from app.features.tickets.approval.service import TicketApprovalService


def _make_scope(*, org_id: str = "dept-001", is_sys_admin: bool = False) -> dict:
    return {"organization_id": org_id, "is_sys_admin": is_sys_admin}


def _make_approval_response() -> ApprovalResponse:
    from app.features.tickets.approval.schemas import ApprovalActorResponse

    return ApprovalResponse(
        id=1,
        ticket_id=10,
        title="test-approval",
        status="pending",
        requester=ApprovalActorResponse(id=1, display_name="requester-001"),
        approver=None,
        comment=None,
        created_at="2026-04-19T00:00:00Z",
        updated_at="2026-04-19T00:00:00Z",
    )


class TestTicketApprovalServiceListApprovals:
    """list_approvals のユニットテスト。"""

    @pytest.mark.asyncio
    async def test_承認一覧取得が成功した場合にOkを返す(self) -> None:
        # Arrange
        expected = ApprovalListResponse(items=[_make_approval_response()], total=1)
        repo = MagicMock()
        repo.list_by_ticket = AsyncMock(return_value=Ok(expected))
        service = TicketApprovalService(repo)

        # Act
        result = await service.list_approvals(ticket_id=10, scope=_make_scope())

        # Assert
        assert result.ok is True
        assert result.value.total == 1

    @pytest.mark.asyncio
    async def test_Repositoryがエラーを返した場合にErrを伝播する(self) -> None:
        # Arrange
        err = Err(AppError(type="NOT_FOUND", message="チケットが見つかりません"))
        repo = MagicMock()
        repo.list_by_ticket = AsyncMock(return_value=err)
        service = TicketApprovalService(repo)

        # Act
        result = await service.list_approvals(ticket_id=99, scope=_make_scope())

        # Assert
        assert result.ok is False
        assert result.error.type == "NOT_FOUND"


class TestTicketApprovalServiceCreateApproval:
    """create_approval のユニットテスト。"""

    @pytest.mark.asyncio
    async def test_承認申請作成が成功した場合にOkを返す(self) -> None:
        # Arrange
        expected = _make_approval_response()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=Ok(expected))
        service = TicketApprovalService(repo)
        req = CreateApprovalRequest(title="test-approval-title")

        # Act
        result = await service.create_approval(
            ticket_id=10,
            req=req,
            requester_id=1,
            scope=_make_scope(),
        )

        # Assert
        assert result.ok is True
        assert result.value.status == "pending"

    @pytest.mark.asyncio
    async def test_チケットが存在しない場合にNOT_FOUNDエラーを伝播する(self) -> None:
        # Arrange
        repo = MagicMock()
        repo.create = AsyncMock(
            return_value=Err(AppError(type="NOT_FOUND", message="チケット ID=99 が見つかりません"))
        )
        service = TicketApprovalService(repo)
        req = CreateApprovalRequest(title="test-approval-title")

        # Act
        result = await service.create_approval(
            ticket_id=99,
            req=req,
            requester_id=1,
            scope=_make_scope(),
        )

        # Assert
        assert result.ok is False
        assert result.error.type == "NOT_FOUND"


class TestTicketApprovalServiceReviewApproval:
    """review_approval のユニットテスト。"""

    @pytest.mark.asyncio
    async def test_承認操作が成功した場合にOkを返す(self) -> None:
        # Arrange
        from app.features.tickets.approval.schemas import ApprovalActorResponse

        approved_response = ApprovalResponse(
            id=1,
            ticket_id=10,
            title="test-approval",
            status="approved",
            requester=ApprovalActorResponse(id=1, display_name="requester-001"),
            approver=ApprovalActorResponse(id=2, display_name="approver-002"),
            comment="承認します",
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:00Z",
        )
        repo = MagicMock()
        repo.review = AsyncMock(return_value=Ok(approved_response))
        service = TicketApprovalService(repo)
        req = ReviewApprovalRequest(action="approve", comment="承認します")

        # Act
        result = await service.review_approval(
            ticket_id=10,
            approval_id=1,
            req=req,
            approver_id=2,
            scope=_make_scope(),
        )

        # Assert
        assert result.ok is True
        assert result.value.status == "approved"

    @pytest.mark.asyncio
    async def test_四眼原則違反の場合にBUSINESS_RULEエラーを伝播する(self) -> None:
        # Arrange
        repo = MagicMock()
        repo.review = AsyncMock(
            return_value=Err(
                AppError(
                    type="BUSINESS_RULE",
                    message="Four-eyes principle: requester and approver must be different users",
                )
            )
        )
        service = TicketApprovalService(repo)
        req = ReviewApprovalRequest(action="approve", comment=None)

        # Act
        result = await service.review_approval(
            ticket_id=10,
            approval_id=1,
            req=req,
            approver_id=1,  # requester_id と同一（四眼原則違反）
            scope=_make_scope(),
        )

        # Assert
        assert result.ok is False
        assert result.error.type == "BUSINESS_RULE"

    @pytest.mark.asyncio
    async def test_却下操作が成功した場合にOkを返す(self) -> None:
        # Arrange
        from app.features.tickets.approval.schemas import ApprovalActorResponse

        rejected_response = ApprovalResponse(
            id=1,
            ticket_id=10,
            title="test-approval",
            status="rejected",
            requester=ApprovalActorResponse(id=1, display_name="requester-001"),
            approver=ApprovalActorResponse(id=2, display_name="approver-002"),
            comment="却下します",
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:00Z",
        )
        repo = MagicMock()
        repo.review = AsyncMock(return_value=Ok(rejected_response))
        service = TicketApprovalService(repo)
        req = ReviewApprovalRequest(action="reject", comment="却下します")

        # Act
        result = await service.review_approval(
            ticket_id=10,
            approval_id=1,
            req=req,
            approver_id=2,
            scope=_make_scope(),
        )

        # Assert
        assert result.ok is True
        assert result.value.status == "rejected"
