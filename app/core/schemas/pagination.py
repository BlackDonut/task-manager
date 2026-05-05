"""カーソルベースページネーション共通スキーマ。

仕様ソース: ``.github/instructions/pagination.instructions.md``

一覧 API の標準はカーソルページネーション（L2）。offset は管理画面限定。
cursor は Base64 エンコードの不透明値（実装は ``app.common.cursor_pagination`` 参照）。
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# カーソルページの最大件数。共通スキーマに集約（Magic number 禁止。L3）
CURSOR_PAGE_DEFAULT_LIMIT: int = 20
CURSOR_PAGE_MAX_LIMIT: int = 100


class CursorPaginationParams(BaseModel):  # type: ignore[explicit-any]
    """カーソルページネーションのクエリパラメータ。"""

    cursor: str | None = Field(default=None, description="次ページ取得用の不透明カーソル")
    limit: int = Field(default=CURSOR_PAGE_DEFAULT_LIMIT, ge=1, le=CURSOR_PAGE_MAX_LIMIT)


class CursorPage[T](BaseModel):  # type: ignore[explicit-any]
    """カーソル形式の一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    next_cursor: str | None = Field(
        default=None,
        description="次ページがあれば不透明カーソル。無ければ None",
    )


class PageMeta(BaseModel):  # type: ignore[explicit-any]
    """offset 形式ページネーションのメタ情報。"""

    total: int
    page: int
    page_size: int
    total_pages: int
