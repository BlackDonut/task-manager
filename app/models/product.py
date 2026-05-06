"""製品テーブルの ORM モデル。"""

from __future__ import annotations

from sqlalchemy import NVARCHAR, ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.project import ProjectOrm


class ProductOrm(Base):
    """products テーブル。プロジェクト配下の製品単位でタスクを管理する。"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False)
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    project: Mapped[ProjectOrm] = relationship("ProjectOrm")
