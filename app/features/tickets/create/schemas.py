"""チケット作成 API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.list.schemas import (
    AssigneeResponse,
    ProductResponse,
    TicketPriority,
    TicketStatus,
    TicketTracker,
)

# ---- リクエスト -----------------------------------------------------------


class TicketCreateRequest(BaseModel):
    """チケット作成リクエスト。"""

    model_config = ConfigDict(from_attributes=True)

    product_id: int = Field(description="所属製品 ID")
    release_id: int | None = Field(default=None, description="作業サイクル ID（product_releases.id）。未指定時はサイクル未分類扱い")
    parent_id: int | None = Field(default=None, description="親チケット ID（None=ルート）")
    tracker: TicketTracker = Field(description="トラッカー")
    status: TicketStatus = Field(default="new", description="ステータス（デフォルト: 新規）")
    priority: TicketPriority = Field(default="normal", description="優先度（デフォルト: 通常）")
    subject: str = Field(min_length=1, max_length=500, description="題名")
    assignee_id: int | None = Field(default=None, description="担当者 ID")
    due_date: datetime.date | None = Field(default=None, description="期日")
    done_ratio: int = Field(default=0, ge=0, le=100, description="進捗率 (%)")
    predecessor_ids: list[int] = Field(
        default_factory=list,
        description="先行チケット ID リスト（Finish-to-Start 依存）",
    )


# ---- レスポンス -----------------------------------------------------------


class TicketCreateResponse(BaseModel):
    """チケット作成レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    product: ProductResponse
    parent_id: int | None
    release_id: int | None = None
    tracker: TicketTracker
    status: TicketStatus
    priority: TicketPriority
    done_ratio: int
    depth: int
    due_date: str | None
    assignee: AssigneeResponse | None
    predecessor_ids: list[int] = Field(default_factory=list)
    updated_at: str
