"""エスカレーションルール API の Pydantic スキーマ定義。

業務制約:
  - alert_days_before: 1 以上の整数（0 以下は業務的に意味なし）
  - escalation_days:   1 以上の整数
  - product_id は変更不可（更新時は別フィールドで再作成）

# co-change: frontend/src/api/endpoints/types.ts EscalationRuleItem / EscalationRuleCreateRequest
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- レスポンス -----------------------------------------------------------


class EscalationRuleItem(BaseModel):
    """エスカレーションルール 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ルール ID")
    product_id: int = Field(description="対象製品 ID")
    product_name: str = Field(description="対象製品名（表示用）")
    alert_days_before: int = Field(description="期日の何日前に通知するか（1 以上）")
    escalation_days: int = Field(description="期日超過から何日後にエスカレーションするか（1 以上）")
    is_active: bool = Field(description="ルールが有効かどうか")


class EscalationRuleListResponse(BaseModel):
    """エスカレーションルール一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[EscalationRuleItem]
    total: int = Field(description="総件数")


class BulkApplyResponse(BaseModel):
    """bulk-apply 実行結果サマリー。

    即時評価した結果として「どのタスクがどのアラート条件に該当するか」を集計して返す。
    Phase 6 通知インフラが整った際は、実際の通知送信数もここに追加する。
    """

    product_id: int = Field(description="評価した製品 ID")
    rule_id: int = Field(description="適用したルール ID")
    alert_target_count: int = Field(
        description=f"現在 alert_days_before 以内に期日が来るタスク件数"
    )
    overdue_count: int = Field(
        description="現在期日超過中のタスク件数"
    )
    escalation_target_count: int = Field(
        description="escalation_days 以上遅延しているタスク件数"
    )
    evaluated_at: str = Field(description="評価実行日時 (ISO 8601)")


# ---- リクエスト -----------------------------------------------------------


class EscalationRuleCreateRequest(BaseModel):
    """エスカレーションルール作成リクエスト。"""

    product_id: int = Field(description="ルールを設定する製品 ID")
    alert_days_before: int = Field(
        default=3,
        ge=1,
        le=365,
        description="期日の何日前に通知するか（1〜365）",
    )
    escalation_days: int = Field(
        default=1,
        ge=1,
        le=365,
        description="期日超過から何日後にエスカレーションするか（1〜365）",
    )
    is_active: bool = Field(default=True, description="有効 / 無効")


class EscalationRuleUpdateRequest(BaseModel):
    """エスカレーションルール更新リクエスト。product_id は変更不可。"""

    alert_days_before: int = Field(
        ge=1,
        le=365,
        description="期日の何日前に通知するか（1〜365）",
    )
    escalation_days: int = Field(
        ge=1,
        le=365,
        description="期日超過から何日後にエスカレーションするか（1〜365）",
    )
    is_active: bool = Field(description="有効 / 無効")
