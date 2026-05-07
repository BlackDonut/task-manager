"""チケット承認テーブルの ORM モデル。

業務上絶対条件 #2 「承認フローの完了確認」の機械的担保。
未承認状態で後続ステータスへ進められないよう、
TicketApprovalOrm の status=pending が存在する間は
チケットの status=in_progress 以降への遷移をブロックする。
"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import UserOrm


class TicketApprovalOrm(Base):
    """ticket_approvals テーブル。

    1 チケットに複数の承認フローを紐付け可能（例: フェーズ移行承認 + 仕様変更承認）。
    状態遷移: pending → approved / rejected
    四眼原則: requester_id != approver_id をアプリ層で強制（validators.py）
    """

    __tablename__ = "ticket_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="承認対象チケット ID"
    )
    requester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, comment="承認申請者 (users.id)"
    )
    approver_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="承認実施者 (users.id)。NULL=未承認",
    )
    # status: pending=承認待ち / approved=承認済み / rejected=却下
    status: Mapped[str] = mapped_column(
        NVARCHAR(20),
        nullable=False,
        default="pending",
        comment="承認ステータス: pending / approved / rejected",
    )
    title: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False, comment="承認タイトル（何の承認か）")
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="承認・却下時のコメント"
    )
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    requester: Mapped[UserOrm] = relationship("UserOrm", foreign_keys=[requester_id])
    approver: Mapped[UserOrm | None] = relationship("UserOrm", foreign_keys=[approver_id])
