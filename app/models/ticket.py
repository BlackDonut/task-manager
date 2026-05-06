"""チケットテーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATE, DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger
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
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    product: Mapped[ProductOrm] = relationship("ProductOrm")
    assignee: Mapped[UserOrm | None] = relationship("UserOrm")
