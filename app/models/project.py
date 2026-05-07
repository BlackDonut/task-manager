"""プロジェクトテーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATE, DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import UserOrm


class ProjectOrm(Base):
    """projects テーブル。"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False)
    # TODO(impact): ALTER TABLE dbo.projects ADD due_date DATE NULL を要実行
    due_date: Mapped[datetime.date | None] = mapped_column(
        DATE, nullable=True, comment="プロジェクト全体の期日"
    )
    # TODO(impact): ALTER TABLE dbo.projects ADD owner_id INT NULL を要実行
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, comment="プロジェクト責任者 (users.id)"
    )
    # TODO(impact): ALTER TABLE dbo.projects ADD created_at DATETIME NOT NULL DEFAULT GETUTCDATE() を要実行
    created_at: Mapped[datetime.datetime | None] = mapped_column(DATETIME, nullable=True)
    # TODO(impact): ALTER TABLE dbo.projects ADD updated_at DATETIME NOT NULL DEFAULT GETUTCDATE() を要実行
    updated_at: Mapped[datetime.datetime | None] = mapped_column(DATETIME, nullable=True)
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    owner: Mapped[UserOrm | None] = relationship("UserOrm")
