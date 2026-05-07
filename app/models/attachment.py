"""チケット添付ファイルテーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import UserOrm


class TicketAttachmentOrm(Base):
    """ticket_attachments テーブル。チケットへの添付ファイルのメタデータを管理する。

    実ファイルは file_storage_root 配下に保存する（Settings.file_storage_root 参照）。
    stored_path は file_storage_root からの相対パスとして保存する。
    """

    __tablename__ = "ticket_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="添付対象チケット ID"
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, comment="アップロード者 (users.id)"
    )
    original_filename: Mapped[str] = mapped_column(
        NVARCHAR(500), nullable=False, comment="元のファイル名（表示用）"
    )
    stored_path: Mapped[str] = mapped_column(
        NVARCHAR(1000), nullable=False, comment="実ファイルパス（file_storage_root からの相対パス）"
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="ファイルサイズ（バイト）")
    content_type: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False, comment="MIME タイプ")
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    uploader: Mapped[UserOrm] = relationship("UserOrm", foreign_keys=[uploader_id])
