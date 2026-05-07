"""エスカレーションルールテーブルの ORM モデル。

製品ごとのアラート条件（期日前通知日数・遅延エスカレーション日数）を管理する。
1 製品につき 1 ルール（product_id に UNIQUE 制約）。

業務制約:
  - delete_flg == 0 フィルタは省略禁止（論理削除 L1）
  - product_id は NOT NULL。グローバルデフォルトは別途定義する場合は拡張する
"""

from __future__ import annotations

import datetime

from sqlalchemy import DATETIME, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.product import ProductOrm


class EscalationRuleOrm(Base):
    """escalation_rules テーブル。製品ごとのアラート条件を定義する。

    alert_days_before: 期日の X 日前にアラート通知を送る
    escalation_days:   期日超過 X 日以上でエスカレーション（上位通知）を送る
    is_active:         0 = 無効 / 1 = 有効
    """

    __tablename__ = "escalation_rules"
    __table_args__ = (
        # 製品ごとに 1 ルールのみ許可
        UniqueConstraint("product_id", name="uq_escalation_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        comment="アラート条件を適用する製品 ID",
    )
    alert_days_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="期日の何日前に通知するか（1 以上の整数）",
    )
    escalation_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="期日超過から何日後にエスカレーションするか（1 以上の整数）",
    )
    is_active: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment="0=無効 / 1=有効",
    )
    delete_flg: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DATETIME, nullable=False)

    # N+1 回避: joinedload で一括取得する（repository 側で指定）
    product: Mapped[ProductOrm] = relationship("ProductOrm")
