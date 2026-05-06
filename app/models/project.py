"""プロジェクトテーブルの ORM モデル。"""

from __future__ import annotations

from sqlalchemy import NVARCHAR, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProjectOrm(Base):
    """projects テーブル。"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False)
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
