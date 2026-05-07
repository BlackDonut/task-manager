"""タスクグループ ORM モデル。

クロス製品・クロスプロジェクトで同一タスクを束ねる多対多グループ管理。
グループ内の任意のチケットが完了（closed / resolved）になると、
同グループの未完了チケットを全件自動完了させる（アプリ層で実施）。

テーブル構成:
  task_groups            … グループのメタ情報 (1 件)
  ticket_group_members   … チケット ↔ グループ の中間テーブル (多対多)
"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TaskGroupOrm(Base):
    """task_groups テーブル。タスクグループのメタ情報を保持する。"""

    __tablename__ = "task_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False, comment="グループ名（例: OS v2 移行作業）")
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="グループ説明（任意）"
    )
    # 論理削除: delete_flg=1 のグループはクエリ・自動完了の対象外とする
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, comment="作成者 user ID"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # メンバー一覧（selectinload で取得する）
    members: Mapped[list[TicketGroupMemberOrm]] = relationship(
        "TicketGroupMemberOrm",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class TicketGroupMemberOrm(Base):
    """ticket_group_members テーブル。チケットとグループの多対多中間テーブル。

    1 チケットが複数グループに所属可能。同一グループへの重複登録は UniqueConstraint で防ぐ。
    """

    __tablename__ = "ticket_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "ticket_id", name="uq_ticket_group_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task_groups.id"), nullable=False, comment="所属グループ ID"
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="メンバーチケット ID"
    )
    added_at: Mapped[datetime.datetime] = mapped_column(
        DATETIME, nullable=False, comment="グループ追加日時"
    )

    group: Mapped[TaskGroupOrm] = relationship("TaskGroupOrm", back_populates="members")
