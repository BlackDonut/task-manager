"""チケットコメント API の Pydantic スキーマ定義。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- リクエスト -----------------------------------------------------------


class CreateCommentRequest(BaseModel):
    """コメント作成リクエスト。"""

    model_config = ConfigDict(from_attributes=True)

    body: str = Field(min_length=1, max_length=10000, description="コメント本文")


# ---- レスポンス -----------------------------------------------------------


class CommentAuthorResponse(BaseModel):
    """コメント投稿者情報。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class CommentResponse(BaseModel):
    """コメント 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author: CommentAuthorResponse
    body: str
    created_at: str
    updated_at: str


class CommentListResponse(BaseModel):
    """コメント一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[CommentResponse]
    total: int
