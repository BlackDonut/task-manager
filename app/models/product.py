"""製品テーブルの ORM モデル。"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, NVARCHAR, ForeignKey, Integer, SmallInteger
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
    releases: Mapped[list[ProductReleaseOrm]] = relationship(
        "ProductReleaseOrm",
        back_populates="product",
        primaryjoin="and_(ProductReleaseOrm.product_id == ProductOrm.id, ProductReleaseOrm.delete_flg == 0)",
        lazy="noload",
    )


# リリースタイプの値はフロントエンドの ReleaseType と同期すること
# co-change: frontend/src/api/endpoints/types.ts ReleaseType
RELEASE_TYPE_INITIAL = "initial"             # 初回リリース
RELEASE_TYPE_SPEC_CHANGE = "spec_change"     # 仕様変更
RELEASE_TYPE_VERSION_UPGRADE = "version_upgrade"  # バージョンアップ
RELEASE_TYPE_MAINTENANCE = "maintenance"     # 保守

# リリースステータスの値はフロントエンドの ReleaseStatus と同期すること
# co-change: frontend/src/api/endpoints/types.ts ReleaseStatus
RELEASE_STATUS_PLANNING = "planning"         # 計画中
RELEASE_STATUS_IN_PROGRESS = "in_progress"  # 進行中
RELEASE_STATUS_COMPLETED = "completed"       # 完了


class ProductReleaseOrm(Base):
    """product_releases テーブル。製品の作業サイクル（初回リリース・仕様変更等）を管理する。

    同一製品に対して複数回の作業（初回リリース後の仕様変更・バージョンアップ等）を
    サイクル単位で追跡するためのエンティティ。
    チケットは release_id（nullable）でサイクルに紐付く。
    """

    __tablename__ = "product_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(NVARCHAR(200), nullable=False, comment="サイクル名 例: v1.0 初回リリース")
    # release_type: RELEASE_TYPE_* 定数参照
    release_type: Mapped[str] = mapped_column(
        NVARCHAR(30),
        nullable=False,
        default=RELEASE_TYPE_INITIAL,
        comment="initial / spec_change / version_upgrade / maintenance",
    )
    # status: RELEASE_STATUS_* 定数参照
    status: Mapped[str] = mapped_column(
        NVARCHAR(20),
        nullable=False,
        default=RELEASE_STATUS_PLANNING,
        comment="planning / in_progress / completed",
    )
    target_date: Mapped[str | None] = mapped_column(
        "target_date",
        NVARCHAR(10),  # DATE型非対応DBへの互換。YYYY-MM-DD文字列で格納
        nullable=True,
        comment="目標完了日 (YYYY-MM-DD)。未設定の場合は NULL",
    )
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    product: Mapped[ProductOrm] = relationship("ProductOrm", back_populates="releases")
