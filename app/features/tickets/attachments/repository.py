"""チケット添付ファイル Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
業務制約:
  - 添付ファイルは論理削除のみ（delete_flg=1）。物理ファイルはファイルサーバに残す。
  - 実ファイルは file_storage_root/tickets/{ticket_id}/ 配下に保存する。
  - ファイルパスはパストラバーサル防止のため safe_join を経由する（L1）。
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.common.upload_validator import OFFICE_ALLOWED_MIME_TYPES, DEFAULT_ALLOWED_MIME_TYPES, validate_and_read_upload
from app.common.utils.path_utils import safe_join, unique_filename
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.config import get_settings
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.attachments.schemas import (
    AttachmentListResponse,
    AttachmentResponse,
    AttachmentUploaderResponse,
)
from app.models.attachment import TicketAttachmentOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="tickets.attachments.repository")

# 添付ファイルで許可する MIME タイプ（PDF + 画像 + Office）
_ALLOWED_MIME_TYPES: frozenset[str] = DEFAULT_ALLOWED_MIME_TYPES | OFFICE_ALLOWED_MIME_TYPES


def _to_response(row: TicketAttachmentOrm) -> AttachmentResponse:
    """ORM → Pydantic レスポンス変換。try スコープ内で呼ぶこと。"""
    return AttachmentResponse(
        id=row.id,
        ticket_id=row.ticket_id,
        original_filename=row.original_filename,
        file_size=row.file_size,
        content_type=row.content_type,
        uploader=AttachmentUploaderResponse(id=row.uploader.id, display_name=row.uploader.display_name),
        created_at=row.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


class TicketAttachmentRepository:
    """チケット添付ファイルのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()
        self._storage_root = Path(get_settings().file_storage_root)

    async def list_by_ticket(
        self,
        ticket_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[AttachmentListResponse]:
        """チケットに紐づく添付ファイル一覧を返す（delete_flg == 0 のみ）。"""
        try:
            stmt = (
                select(TicketAttachmentOrm)
                .options(joinedload(TicketAttachmentOrm.uploader))
                .where(
                    TicketAttachmentOrm.ticket_id == ticket_id,
                    TicketAttachmentOrm.delete_flg == 0,
                )
                .order_by(TicketAttachmentOrm.created_at)
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()
            items = [_to_response(r) for r in rows]
            return Ok(AttachmentListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("tickets.attachments.list.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="添付ファイル一覧の取得に失敗しました", details=exc))

    async def upload(
        self,
        ticket_id: int,
        upload: object,  # FastAPI UploadFile; import at call site to avoid circular
        uploader_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[AttachmentResponse]:
        """添付ファイルをアップロードしてメタデータをDBに保存する。

        ファイルはパストラバーサル防止付きの safe_join で保存先を決定する。
        MIME タイプ・サイズ検証は upload_validator.validate_and_read_upload で実施。
        """
        try:
            ticket = await self._session.get(TicketOrm, ticket_id)
            if ticket is None or ticket.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"チケット ID={ticket_id} が見つかりません"))

            # MIME タイプ・サイズ検証（L1: 外部入力のバリデーション）
            validate_result = await validate_and_read_upload(
                upload,  # type: ignore[arg-type]
                allowed_mime_types=_ALLOWED_MIME_TYPES,
            )
            if not validate_result.ok:
                return validate_result  # type: ignore[return-value]
            file_bytes = validate_result.value

            # パストラバーサル防止付きの保存先決定
            base_dir = self._storage_root / "tickets" / str(ticket_id)
            original_name: str = getattr(upload, "filename", "upload") or "upload"
            safe_name = unique_filename(original_name)
            join_result = safe_join(base_dir, safe_name)
            if not join_result.ok:
                return join_result  # type: ignore[return-value]
            dest_path = join_result.value

            # ディレクトリ作成 + ファイル書き込み（ブロッキング IO を executor で実行）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: (dest_path.parent.mkdir(parents=True, exist_ok=True), dest_path.write_bytes(file_bytes)))

            # DB メタデータ保存
            content_type: str = getattr(upload, "content_type", "application/octet-stream") or "application/octet-stream"
            now = self._clock.now()
            attachment = TicketAttachmentOrm(
                ticket_id=ticket_id,
                uploader_id=uploader_id,
                original_filename=original_name,
                stored_path=str(dest_path.relative_to(self._storage_root)),
                file_size=len(file_bytes),
                content_type=content_type,
                delete_flg=0,
                created_at=now,
            )
            self._session.add(attachment)
            await self._session.flush()

            stmt = (
                select(TicketAttachmentOrm)
                .options(joinedload(TicketAttachmentOrm.uploader))
                .where(TicketAttachmentOrm.id == attachment.id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()
            response = _to_response(row)
            await self._session.commit()
            logger.info(
                "tickets.attachments.uploaded",
                ticket_id=ticket_id,
                attachment_id=attachment.id,
                file_size=len(file_bytes),
            )
            return Ok(response)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.attachments.upload.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="添付ファイルのアップロードに失敗しました", details=exc))

    async def delete(
        self,
        ticket_id: int,
        attachment_id: int,
        user_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[None]:
        """添付ファイルを論理削除する。アップロード者本人のみ削除可能。

        物理ファイルは削除しない（監査証跡保持）。
        """
        try:
            attachment = await self._session.get(TicketAttachmentOrm, attachment_id)
            if attachment is None or attachment.delete_flg != 0 or attachment.ticket_id != ticket_id:
                return Err(AppError(type="NOT_FOUND", message=f"添付ファイル ID={attachment_id} が見つかりません"))

            if attachment.uploader_id != user_id:
                return Err(AppError(type="FORBIDDEN", message="添付ファイルを削除できるのはアップロード者本人のみです"))

            attachment.delete_flg = 1
            await self._session.commit()
            logger.info("tickets.attachments.deleted", attachment_id=attachment_id)
            return Ok(None)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.attachments.delete.error", attachment_id=attachment_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="添付ファイルの削除に失敗しました", details=exc))
