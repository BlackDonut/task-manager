"""チケット承認 Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Service 層に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.approval.repository import TicketApprovalRepository
from app.features.tickets.approval.schemas import (
    ApprovalListResponse,
    ApprovalResponse,
    CreateApprovalRequest,
    ReviewApprovalRequest,
)
from app.features.tickets.approval.service import TicketApprovalService

logger = get_logger(component="tickets.approval")

router = APIRouter(prefix="/api/v1/tickets", tags=["ticket-approvals"])


def _get_service(session: AsyncSession = Depends(get_db)) -> TicketApprovalService:
    return TicketApprovalService(TicketApprovalRepository(session))


@router.get(
    "/{ticket_id}/approvals",
    response_model=ApprovalListResponse,
    summary="チケット承認一覧取得",
    description="指定チケットの承認フロー一覧を返す。",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_approvals(
    request: Request,
    ticket_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketApprovalService = Depends(_get_service),
) -> ApprovalListResponse:
    """チケットの承認一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("tickets.approval.list.request", ticket_id=ticket_id, user_id=user.id, request_id=request_id)
    result = await service.list_approvals(ticket_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    return result.value


@router.post(
    "/{ticket_id}/approvals",
    response_model=ApprovalResponse,
    status_code=201,
    summary="承認申請作成",
    description="チケットに承認申請を作成する。pending 承認が存在する間はチケットの進行ステータスへの変更がブロックされる。",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def create_approval(
    request: Request,
    ticket_id: int,
    body: CreateApprovalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketApprovalService = Depends(_get_service),
) -> ApprovalResponse:
    """承認申請を作成する。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "tickets.approval.create.request",
        ticket_id=ticket_id,
        user_id=user.id,
        request_id=request_id,
    )
    # ASSUMPTION: AuthenticatedUser.id は UserOrm.id（int PK）と対応する数値文字列を想定。
    # セッション設計（session.py §user_id）との整合確認が必要。
    # TODO(domain): 認証設計確定後に user.id の型を int か str か統一すること。
    try:
        requester_int_id = int(user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "ユーザーIDが数値形式ではありません"},
        )
    result = await service.create_approval(
        ticket_id=ticket_id,
        req=body,
        requester_id=requester_int_id,
        scope=user.scope,
    )
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    logger.info(
        "tickets.approval.create.response",
        approval_id=result.value.id,
        user_id=user.id,
        request_id=request_id,
    )
    return result.value


@router.patch(
    "/{ticket_id}/approvals/{approval_id}",
    response_model=ApprovalResponse,
    summary="承認・却下",
    description="承認申請を承認または却下する。四眼原則により申請者本人は承認不可。",
    dependencies=[permission_required(Actions.APPROVE, Resources.TASK)],
)
async def review_approval(
    request: Request,
    ticket_id: int,
    approval_id: int,
    body: ReviewApprovalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TicketApprovalService = Depends(_get_service),
) -> ApprovalResponse:
    """承認または却下を実行する。四眼原則は Service → Repository で検証する。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "tickets.approval.review.request",
        ticket_id=ticket_id,
        approval_id=approval_id,
        action=body.action,
        user_id=user.id,
        request_id=request_id,
    )
    # ASSUMPTION: AuthenticatedUser.id は UserOrm.id（int PK）と対応する数値文字列を想定。
    try:
        approver_int_id = int(user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "ユーザーIDが数値形式ではありません"},
        )
    result = await service.review_approval(
        ticket_id=ticket_id,
        approval_id=approval_id,
        req=body,
        approver_id=approver_int_id,
        scope=user.scope,
    )
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    logger.info(
        "tickets.approval.review.response",
        approval_id=approval_id,
        action=body.action,
        user_id=user.id,
        request_id=request_id,
    )
    return result.value

