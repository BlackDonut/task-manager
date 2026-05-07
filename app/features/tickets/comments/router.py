"""チケットコメント Router。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.comments.repository import TicketCommentRepository
from app.features.tickets.comments.schemas import (
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
)

logger = get_logger(component="tickets.comments")

router = APIRouter(prefix="/api/v1/tickets", tags=["ticket-comments"])


def _get_repository(session: AsyncSession = Depends(get_db)) -> TicketCommentRepository:
    return TicketCommentRepository(session)


@router.get(
    "/{ticket_id}/comments",
    response_model=CommentListResponse,
    summary="チケットコメント一覧取得",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_comments(
    request: Request,
    ticket_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketCommentRepository = Depends(_get_repository),
) -> CommentListResponse:
    """チケットのコメント一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("tickets.comments.list.request", ticket_id=ticket_id, user_id=user.id, request_id=request_id)
    result = await repository.list_by_ticket(ticket_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    return result.value


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="コメント作成",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def create_comment(
    request: Request,
    ticket_id: int,
    body: CreateCommentRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketCommentRepository = Depends(_get_repository),
) -> CommentResponse:
    """コメントを作成する。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("tickets.comments.create.request", ticket_id=ticket_id, user_id=user.id, request_id=request_id)
    # ASSUMPTION: AuthenticatedUser.id は UserOrm.id（int PK）と対応する数値文字列を想定。
    # TODO(domain): 認証設計確定後に user.id の型を統一すること。
    try:
        author_int_id = int(user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "ユーザーIDが数値形式ではありません"},
        )
    result = await repository.create(ticket_id, body, author_int_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    logger.info("tickets.comments.create.response", comment_id=result.value.id, request_id=request_id)
    return result.value


@router.delete(
    "/{ticket_id}/comments/{comment_id}",
    status_code=204,
    summary="コメント削除",
    description="投稿者本人のみ削除可能（論理削除）。",
    dependencies=[permission_required(Actions.DELETE, Resources.TASK)],
)
async def delete_comment(
    request: Request,
    ticket_id: int,
    comment_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketCommentRepository = Depends(_get_repository),
) -> None:
    """コメントを論理削除する。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "tickets.comments.delete.request",
        ticket_id=ticket_id,
        comment_id=comment_id,
        user_id=user.id,
        request_id=request_id,
    )
    # ASSUMPTION: AuthenticatedUser.id は UserOrm.id（int PK）と対応する数値文字列を想定。
    try:
        user_int_id = int(user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "ユーザーIDが数値形式ではありません"},
        )
    result = await repository.delete(ticket_id, comment_id, user_int_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
