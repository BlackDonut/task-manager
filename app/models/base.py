"""SQLAlchemy ORM 基底クラス。全モデルはここから継承する。"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """共有メタデータを持つ DeclarativeBase。"""
