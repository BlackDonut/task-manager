"""チケット一覧 API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---- 定数 ---------------------------------------------------------------

TicketStatus = Literal[
    "new",          # 新規
    "in_progress",  # 進行中
    "resolved",     # 解決済み
    "closed",       # 終了
    "rejected",     # 却下
]

TicketPriority = Literal[
    "urgent",   # 緊急
    "high",     # 高
    "normal",   # 通常
    "low",      # 低
]

TicketTracker = Literal[
    "bug",          # バグ
    "feature",      # 機能
    "support",      # サポート
    "task",         # タスク
]

# ---- レスポンス -----------------------------------------------------------


class AssigneeResponse(BaseModel):
    """担当者情報。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class ProductResponse(BaseModel):
    """製品情報（チケットの属鞣として返却）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TicketResponse(BaseModel):
    """チケット 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="チケット番号（表示用 ID）")
    product: ProductResponse
    parent_id: int | None = Field(default=None, description="親チケット ID。ルートチケットの場合は None")
    tracker: TicketTracker
    status: TicketStatus
    priority: TicketPriority
    subject: str = Field(description="題名")
    assignee: AssigneeResponse | None = Field(default=None, description="担当者（未割当の場合は None）")
    due_date: str | None = Field(default=None, description="期日 (YYYY-MM-DD)。未設定の場合は None")
    updated_at: str = Field(description="最終更新日時 (ISO 8601 UTC)")
    done_ratio: int = Field(ge=0, le=100, description="進捗率 (%)")


class TicketListResponse(BaseModel):
    """チケット一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[TicketResponse]
    total: int = Field(description="フィルタ後の総件数")
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


# ---- クエリパラメータ -------------------------------------------------------


class TicketListQuery(BaseModel):
    """チケット一覧のフィルタ・ページネーション用クエリパラメータ。"""

    model_config = ConfigDict(from_attributes=True)

    project_id: int | None = Field(default=None, description="プロジェクト ID でフィルタ（製品経由で絞り込む）")
    product_id: int | None = Field(default=None, description="製品 ID でフィルタ（直接指定）")
    status: TicketStatus | None = Field(default=None, description="ステータスでフィルタ")
    priority: TicketPriority | None = Field(default=None, description="優先度でフィルタ")
    tracker: TicketTracker | None = Field(default=None, description="トラッカーでフィルタ")
    assignee_id: int | None = Field(default=None, description="担当者 ID でフィルタ")
    keyword: str | None = Field(default=None, description="題名・本文の部分一致キーワード")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
