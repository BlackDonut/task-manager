"""ガントチャート API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.list.schemas import (
    AssigneeResponse,
    TicketPriority,
    TicketStatus,
    TicketTracker,
)

# ---- レスポンス -----------------------------------------------------------


class GanttProductResponse(BaseModel):
    """ガントチャート用製品レスポンス。project_id を含む（プロジェクト横断グループ化に使用）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int = Field(description="所属プロジェクト ID（プロジェクト単位グループ化に使用）")


class GanttTicketResponse(BaseModel):
    """ガントチャート 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="チケット番号（表示用 ID）")
    subject: str = Field(description="題名")
    product: GanttProductResponse
    parent_id: int | None = Field(default=None, description="親チケット ID。ルートチケットの場合は None")
    status: TicketStatus
    priority: TicketPriority
    tracker: TicketTracker
    done_ratio: int = Field(ge=0, le=100, description="進捗率 (%)")
    depth: int = Field(ge=0, le=3, default=0, description="階層深度。0=ルート/フェーズ, 1=子, 2=孫, 3=曾孫")
    start_date: str = Field(description="開始日 (YYYY-MM-DD)。チケット作成日を使用")
    due_date: str | None = Field(default=None, description="期日 (YYYY-MM-DD)。未設定の場合は None")
    assignee: AssigneeResponse | None = Field(default=None, description="担当者（未割当の場合は None）")
    predecessor_ids: list[int] = Field(default_factory=list, description="先行チケット ID リスト（前後関係）")


class GanttTicketListResponse(BaseModel):
    """ガントチャート一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[GanttTicketResponse]
    total: int = Field(description="フィルタ後の総件数（最大 500 件）")


# ---- クエリパラメータ -------------------------------------------------------


class GanttTicketQuery(BaseModel):
    """ガントチャートのフィルタ用クエリパラメータ。"""

    model_config = ConfigDict(from_attributes=True)

    project_id: int | None = Field(default=None, description="プロジェクト ID でフィルタ（製品経由で絞り込む）")
    product_id: int | None = Field(default=None, description="製品 ID でフィルタ（直接指定）")
    status: TicketStatus | None = Field(default=None, description="ステータスでフィルタ")
    tracker: TicketTracker | None = Field(default=None, description="トラッカーでフィルタ")
    priority: TicketPriority | None = Field(default=None, description="優先度でフィルタ")
    assignee_id: int | None = Field(default=None, description="担当者 ID でフィルタ")
