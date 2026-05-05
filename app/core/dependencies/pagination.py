"""ページネーション FastAPI Depends。

仕様ソース:
- ``docs/01_requirements/folder-structure.md``
- ``.github/instructions/pagination.instructions.md``

一覧 API のページネーションパラメータを Depends として提供する。

    from app.core.dependencies.pagination import get_cursor_pagination, get_offset_pagination
"""

from __future__ import annotations

from fastapi import Query

from app.core.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, OffsetPaginationParams
from app.core.schemas.pagination import (
    CURSOR_PAGE_DEFAULT_LIMIT,
    CURSOR_PAGE_MAX_LIMIT,
    CursorPaginationParams,
)


def get_offset_pagination(
    page: int = Query(default=1, ge=1, description="ページ番号（1 始まり）"),
    page_size: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="1 ページあたりの件数",
    ),
) -> OffsetPaginationParams:
    """offset ベースページネーション Depends（管理画面専用）。

    一般の一覧 API はカーソルページネーション（``get_cursor_pagination``）を使うこと。
    """
    return OffsetPaginationParams(page=page, page_size=page_size)


def get_cursor_pagination(
    cursor: str | None = Query(default=None, description="次ページ取得用の不透明カーソル"),
    limit: int = Query(
        default=CURSOR_PAGE_DEFAULT_LIMIT,
        ge=1,
        le=CURSOR_PAGE_MAX_LIMIT,
        description="取得件数",
    ),
) -> CursorPaginationParams:
    """カーソルベースページネーション Depends（一覧 API 標準）。"""
    return CursorPaginationParams(cursor=cursor, limit=limit)
