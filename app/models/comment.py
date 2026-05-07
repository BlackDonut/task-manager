"""チケットコメントテーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import UserOrm


class TicketCommentOrm(Base):
    """ticket_comments テーブル。チケットへのコメント・エビデンス記録を管理する。"""

    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="コメント対象チケット ID"
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, comment="投稿者 (users.id)"
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, comment="コメント本文")
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    author: Mapped[UserOrm] = relationship("UserOrm", foreign_keys=[author_id])
