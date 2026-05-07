"""チケットコメント Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
業務制約:
  - コメントは論理削除のみ（delete_flg=1）。物理削除禁止。
  - 削除は投稿者本人のみ可能（Router 層で user_id == author_id を確認すること）
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.tickets.comments.schemas import (
    CommentAuthorResponse,
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
)
from app.models.comment import TicketCommentOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="tickets.comments.repository")


def _to_response(row: TicketCommentOrm) -> CommentResponse:
    """ORM → Pydantic レスポンス変換。try スコープ内で呼ぶこと。"""
    return CommentResponse(
        id=row.id,
        ticket_id=row.ticket_id,
        author=CommentAuthorResponse(id=row.author.id, display_name=row.author.display_name),
        body=row.body,
        created_at=row.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        updated_at=row.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


class TicketCommentRepository:
    """チケットコメントのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()

    async def list_by_ticket(
        self,
        ticket_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[CommentListResponse]:
        """チケットに紐づくコメント一覧を返す（delete_flg == 0 のみ、投稿順）。"""
        try:
            stmt = (
                select(TicketCommentOrm)
                .options(joinedload(TicketCommentOrm.author))
                .where(
                    TicketCommentOrm.ticket_id == ticket_id,
                    TicketCommentOrm.delete_flg == 0,
                )
                .order_by(TicketCommentOrm.created_at)
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()
            items = [_to_response(r) for r in rows]
            return Ok(CommentListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("tickets.comments.list.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="コメント一覧の取得に失敗しました", details=exc))

    async def create(
        self,
        ticket_id: int,
        req: CreateCommentRequest,
        author_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[CommentResponse]:
        """コメントを作成する。"""
        try:
            ticket = await self._session.get(TicketOrm, ticket_id)
            if ticket is None or ticket.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"チケット ID={ticket_id} が見つかりません"))

            now = self._clock.now()
            comment = TicketCommentOrm(
                ticket_id=ticket_id,
                author_id=author_id,
                body=req.body,
                delete_flg=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(comment)
            await self._session.flush()

            stmt = (
                select(TicketCommentOrm)
                .options(joinedload(TicketCommentOrm.author))
                .where(TicketCommentOrm.id == comment.id)
            )
            row = (await self._session.execute(stmt)).unique().scalar_one()
            response = _to_response(row)
            await self._session.commit()
            logger.info("tickets.comments.created", ticket_id=ticket_id, comment_id=comment.id)
            return Ok(response)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.comments.create.error", ticket_id=ticket_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="コメントの作成に失敗しました", details=exc))

    async def delete(
        self,
        ticket_id: int,
        comment_id: int,
        user_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[None]:
        """コメントを論理削除する。投稿者本人のみ削除可能。"""
        try:
            comment = await self._session.get(TicketCommentOrm, comment_id)
            if comment is None or comment.delete_flg != 0 or comment.ticket_id != ticket_id:
                return Err(AppError(type="NOT_FOUND", message=f"コメント ID={comment_id} が見つかりません"))

            if comment.author_id != user_id:
                return Err(AppError(
                    type="FORBIDDEN",
                    message="コメントを削除できるのは投稿者本人のみです",
                ))

            comment.delete_flg = 1
            comment.updated_at = self._clock.now()
            await self._session.commit()
            logger.info("tickets.comments.deleted", comment_id=comment_id)
            return Ok(None)
        except Exception as exc:
            await self._session.rollback()
            logger.error("tickets.comments.delete.error", comment_id=comment_id, error=str(exc))
            return Err(AppError(type="INTERNAL", message="コメントの削除に失敗しました", details=exc))
