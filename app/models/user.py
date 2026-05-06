"""ユーザーテーブルの ORM モデル。"""

from __future__ import annotations

from sqlalchemy import NVARCHAR, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserOrm(Base):
    """users テーブル。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(NVARCHAR(100), nullable=False)
    display_name: Mapped[str] = mapped_column(NVARCHAR(100), nullable=False)
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
