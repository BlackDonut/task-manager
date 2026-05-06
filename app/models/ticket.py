"""チケットテーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATE, DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.product import ProductOrm
from app.models.user import UserOrm


class TicketOrm(Base):
    """tickets テーブル。"""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=True)
    tracker: Mapped[str] = mapped_column(NVARCHAR(20), nullable=False)
    status: Mapped[str] = mapped_column(NVARCHAR(20), nullable=False)
    priority: Mapped[str] = mapped_column(NVARCHAR(20), nullable=False)
    subject: Mapped[str] = mapped_column(NVARCHAR(500), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    due_date: Mapped[datetime.date | None] = mapped_column(DATE, nullable=True)
    done_ratio: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # TODO(impact): ALTER TABLE dbo.tickets ADD depth INT NOT NULL DEFAULT 0 を要実行
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="階層深度。0=ルート/フェーズ, 1=子, 2=孫, 3=曾孫。最大値=3をアプリ層で強制")
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    product: Mapped[ProductOrm] = relationship("ProductOrm")
    assignee: Mapped[UserOrm | None] = relationship("UserOrm")

    # 前後関係: このチケットが後続する先行チケットの依存レコード一覧
    # selectinload で一括取得する（repository 側で指定）
    dependencies_as_successor: Mapped[list[TicketDependencyOrm]] = relationship(
        "TicketDependencyOrm",
        foreign_keys="[TicketDependencyOrm.successor_id]",
    )


class TicketDependencyOrm(Base):
    """ticket_dependencies テーブル。チケット間の前後関係（先行/後続）を管理する。

    predecessor_id のチケットが完了してから successor_id のチケットを開始するという
    Finish-to-Start 依存を表す。
    """

    __tablename__ = "ticket_dependencies"
    __table_args__ = (
        UniqueConstraint("predecessor_id", "successor_id", name="uq_ticket_dep"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    predecessor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="先行チケット ID"
    )
    successor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=False, comment="後続チケット ID"
    )
