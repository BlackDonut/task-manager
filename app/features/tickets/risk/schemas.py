"""リスクダッシュボード API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと

対象エンドポイント: GET /api/v1/tickets/risk-summary
目的: 遅延・未割当・期限直前チケットの集計と一覧を返し、SCR003 ダッシュボードに提供する。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.list.schemas import (
    AssigneeResponse,
    ProductResponse,
    TicketPriority,
    TicketStatus,
    TicketTracker,
)

# ---- サマリー -----------------------------------------------------------


class RiskSummary(BaseModel):
    """画面上部のサマリーカード用集計値。"""

    model_config = ConfigDict(from_attributes=True)

    overdue_count: int = Field(description="期限超過チケット数（status が resolved/closed/rejected 以外）")
    at_risk_count: int = Field(description="期限 3 日以内チケット数（未超過・未完了）")
    unassigned_count: int = Field(description="担当者未割当の未完了チケット数")
    in_progress_count: int = Field(description="new + in_progress の合計チケット数")


class ProductRiskSummary(BaseModel):
    """製品別の進捗・遅延集計。"""

    model_config = ConfigDict(from_attributes=True)

    product: ProductResponse
    total_count: int = Field(description="製品配下の全チケット数（論理削除除外）")
    avg_progress: int = Field(ge=0, le=100, description="進捗率の平均 (%)")
    overdue_count: int = Field(description="期限超過チケット数（未完了のみ）")


# ---- リスクチケット一覧 --------------------------------------------------


class RiskTicketResponse(BaseModel):
    """リスク一覧に表示するチケット 1 件。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="チケット番号")
    subject: str = Field(description="題名")
    product: ProductResponse
    status: TicketStatus
    priority: TicketPriority
    tracker: TicketTracker
    due_date: str | None = Field(default=None, description="期日 (YYYY-MM-DD)。未設定の場合は None")
    overdue_days: int = Field(
        description="期限超過日数。正値＝超過日数、負値＝残り日数、0＝当日。due_date が None の場合は 0"
    )
    assignee: AssigneeResponse | None = Field(default=None, description="担当者（未割当の場合は None）")
    done_ratio: int = Field(ge=0, le=100, description="進捗率 (%)")
    predecessor_ids: list[int] = Field(default_factory=list, description="先行チケット ID リスト（前後関係）")


# ---- レスポンス全体 ------------------------------------------------------


class RiskDashboardResponse(BaseModel):
    """リスクダッシュボードの全体レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    summary: RiskSummary
    product_summaries: list[ProductRiskSummary] = Field(
        description="製品別進捗・遅延集計（overdue_count 降順・product.id 昇順）"
    )
    risk_tickets: list[RiskTicketResponse] = Field(
        description="遅延中 + 期限 3 日以内のチケット（期日昇順・未割当優先）。最大 200 件"
    )


# ---- クエリパラメータ ---------------------------------------------------


class RiskDashboardQuery(BaseModel):
    """リスクダッシュボードのフィルタ用クエリパラメータ。"""

    model_config = ConfigDict(from_attributes=True)

    project_id: int | None = Field(default=None, description="プロジェクト ID でフィルタ（製品経由で絞り込む）")
