"""フェーズ進捗マトリクス API の Pydantic スキーマ定義。

対象エンドポイント: GET /api/v1/tickets/phase-matrix
目的: 製品×フェーズのクロス集計マトリクスを返し、SCR005 フェーズゲート確認画面に提供する。

フェーズ = tracker=='phase' のチケット。
完了判定 = status が 'resolved' または 'closed'。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.features.tickets.list.schemas import ProductResponse


class PhaseState(str, Enum):
    """フェーズセルの状態区分。

    - completed:   resolved または closed
    - overdue:     active（new / in_progress）かつ due_date < 今日
    - in_progress: in_progress かつ期限超過なし
    - not_started: new かつ期限超過なし
    - rejected:    rejected
    - none:        この製品にフェーズチケットが存在しない
    """

    completed = "completed"
    overdue = "overdue"
    in_progress = "in_progress"
    not_started = "not_started"
    rejected = "rejected"
    none = "none"


class PhaseCell(BaseModel):
    """マトリクスのセル 1 件。phases リストと同順。"""

    model_config = ConfigDict(from_attributes=True)

    phase_subject: str = Field(description="フェーズ名（チケット題名）")
    ticket_id: int | None = Field(default=None, description="チケット ID。フェーズチケットが存在しない場合は None")
    status: str | None = Field(default=None, description="チケットステータス。フェーズチケットが存在しない場合は None")
    due_date: str | None = Field(default=None, description="期日 (YYYY-MM-DD)。未設定または存在しない場合は None")
    state: PhaseState = Field(description="セルの状態区分（完了/遅延/進行中/未着手/却下/なし）")


class ProductPhaseRow(BaseModel):
    """製品 1 行分のデータ。"""

    model_config = ConfigDict(from_attributes=True)

    product: ProductResponse
    cells: list[PhaseCell] = Field(description="phases リストと同順のセル一覧")


class PhaseMatrixQuery(BaseModel):
    """フェーズ進捗マトリクスのクエリパラメータ。"""

    project_id: int | None = Field(default=None, description="プロジェクト ID でフィルタ。None = 全プロジェクト")


class PhaseMatrixResponse(BaseModel):
    """フェーズ進捗マトリクスのレスポンス全体。"""

    model_config = ConfigDict(from_attributes=True)

    phases: list[str] = Field(description="全製品にわたるフェーズ名の昇順ソート一覧（列定義）")
    rows: list[ProductPhaseRow] = Field(description="製品ごとの行。phases と同順のセルを持つ")
