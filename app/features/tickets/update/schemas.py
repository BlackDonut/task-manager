"""チケット更新 API の Pydantic スキーマ定義。

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


class TicketUpdateRequest(BaseModel):
    """チケット更新リクエスト。

    product_id は変更不可。その他の編集可能フィールドを一括で更新する（PUT 相当）。
    """

    model_config = ConfigDict(from_attributes=True)

    tracker: TicketTracker = Field(description="トラッカー")
    status: TicketStatus = Field(description="ステータス")
    priority: TicketPriority = Field(description="優先度")
    subject: str = Field(min_length=1, max_length=500, description="題名")
    release_id: int | None = Field(default=None, description="作業サイクル ID（product_releases.id）")
    assignee_id: int | None = Field(default=None, description="担当者 ID（None=未割当）")
    due_date: datetime.date | None = Field(default=None, description="期日（None=未設定）")
    done_ratio: int = Field(default=0, ge=0, le=100, description="進捗率 (%)")
    parent_id: int | None = Field(default=None, description="親チケット ID（None=ルート）")
    predecessor_ids: list[int] = Field(
        default_factory=list,
        description="先行チケット ID リスト（Finish-to-Start 依存）",
    )


# ---- レスポンス -----------------------------------------------------------


class TicketUpdateResponse(BaseModel):
    """チケット更新レスポンス。"""

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
