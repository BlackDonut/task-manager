"""チケット添付ファイル Router。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.tickets.attachments.repository import TicketAttachmentRepository
from app.features.tickets.attachments.schemas import AttachmentListResponse, AttachmentResponse

logger = get_logger(component="tickets.attachments")

router = APIRouter(prefix="/api/v1/tickets", tags=["ticket-attachments"])


def _get_repository(session: AsyncSession = Depends(get_db)) -> TicketAttachmentRepository:
    return TicketAttachmentRepository(session)


@router.get(
    "/{ticket_id}/attachments",
    response_model=AttachmentListResponse,
    summary="添付ファイル一覧取得",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_attachments(
    request: Request,
    ticket_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketAttachmentRepository = Depends(_get_repository),
) -> AttachmentListResponse:
    """チケットの添付ファイル一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("tickets.attachments.list.request", ticket_id=ticket_id, user_id=user.id, request_id=request_id)
    result = await repository.list_by_ticket(ticket_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    return result.value


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
    summary="添付ファイルアップロード",
    description="チケットにファイルを添付する。許可形式: PDF / 画像 / Word / Excel。最大 20 MB。",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def upload_attachment(
    request: Request,
    ticket_id: int,
    file: UploadFile,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketAttachmentRepository = Depends(_get_repository),
) -> AttachmentResponse:
    """添付ファイルをアップロードする。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "tickets.attachments.upload.request",
        ticket_id=ticket_id,
        user_id=user.id,
        filename=file.filename,
        request_id=request_id,
    )
    # ASSUMPTION: AuthenticatedUser.id は UserOrm.id（int PK）と対応する数値文字列を想定。
    # TODO(domain): 認証設計確定後に user.id の型を統一すること。
    try:
        uploader_int_id = int(user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "ユーザーIDが数値形式ではありません"},
        )
    result = await repository.upload(ticket_id, file, uploader_int_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
    logger.info(
        "tickets.attachments.upload.response",
        attachment_id=result.value.id,
        user_id=user.id,
        request_id=request_id,
    )
    return result.value


@router.delete(
    "/{ticket_id}/attachments/{attachment_id}",
    status_code=204,
    summary="添付ファイル削除",
    description="添付ファイルを論理削除する。アップロード者本人のみ削除可能。",
    dependencies=[permission_required(Actions.DELETE, Resources.TASK)],
)
async def delete_attachment(
    request: Request,
    ticket_id: int,
    attachment_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TicketAttachmentRepository = Depends(_get_repository),
) -> None:
    """添付ファイルを論理削除する。"""
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "tickets.attachments.delete.request",
        ticket_id=ticket_id,
        attachment_id=attachment_id,
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
    result = await repository.delete(ticket_id, attachment_id, user_int_id, user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)
