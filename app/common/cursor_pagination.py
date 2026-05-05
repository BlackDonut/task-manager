"""カーソルベースページネーション。

仕様ソース:
- ``docs/03_detail-design/01_common/common-backend.md`` §5.7
- ``.github/instructions/pagination.instructions.md``

- cursor は Base64URL エンコードの不透明値。クライアントには ID を露出しない
- 呼び出し側は ``limit + 1`` 件取得し、``build_cursor_page`` に渡すことで next_cursor が決まる

ASSUMPTION: カーソルはエンティティの ``id`` 文字列をそのまま Base64URL する単純実装。
将来、複合キー（例: created_at + id）でのソートが必要になったら ADR を起こして変更する。
"""

from __future__ import annotations

import base64
import binascii
from typing import Protocol, TypeVar

from app.core.result import AppError, Err, Ok, Result
from app.core.schemas.pagination import CursorPage


class _HasId(Protocol):
    """``id`` 属性を持つことを要求する Protocol（エンティティ想定）。"""

    @property
    def id(self) -> str: ...


T = TypeVar("T", bound=_HasId)


def encode_cursor(entity_id: str) -> str:
    """エンティティ ID を不透明カーソルにエンコードする。"""
    return base64.urlsafe_b64encode(entity_id.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> Result[str | None]:
    """不透明カーソルをデコードしてエンティティ ID を返す。

    不正なカーソルは VALIDATION エラーで返す。
    """
    if cursor is None:
        return Ok(value=None)
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return Err(error=AppError(type="VALIDATION", message="Invalid cursor"))
    return Ok(value=decoded)


def build_cursor_page[T: _HasId](items: list[T], limit: int) -> CursorPage[T]:
    """取得結果（``limit + 1`` 件）から ``CursorPage`` を構築する。

    - ``items`` が ``limit`` 件以下: 次ページなし。全件返却
    - ``items`` が ``limit + 1`` 件以上: ``limit`` 件まで返却し、最終要素の ID を cursor 化
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    has_next = len(items) > limit
    actual_items = items[:limit] if has_next else items
    next_cursor: str | None = None
    if has_next and actual_items:
        next_cursor = encode_cursor(actual_items[-1].id)
    return CursorPage(items=actual_items, next_cursor=next_cursor)
