"""チケット承認 API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 承認ステータスの型エイリアス
ApprovalStatus = Literal["pending", "approved", "rejected"]

# 承認アクション（PATCH 時に指定）
ApprovalAction = Literal["approve", "reject"]


# ---- リクエスト -----------------------------------------------------------


class CreateApprovalRequest(BaseModel):
    """承認申請作成リクエスト。"""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=200, description="承認タイトル（何の承認か）")


class ReviewApprovalRequest(BaseModel):
    """承認・却下リクエスト。

    四眼原則: Router 層で申請者 != 承認者を検証する。
    """

    model_config = ConfigDict(from_attributes=True)

    action: ApprovalAction = Field(description="承認操作: approve=承認 / reject=却下")
    comment: str | None = Field(default=None, max_length=2000, description="承認・却下コメント")


# ---- レスポンス -----------------------------------------------------------


class ApprovalActorResponse(BaseModel):
    """承認関係者情報。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class ApprovalResponse(BaseModel):
    """承認 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    title: str
    status: ApprovalStatus
    requester: ApprovalActorResponse
    approver: ApprovalActorResponse | None = None
    comment: str | None = None
    created_at: str
    updated_at: str


class ApprovalListResponse(BaseModel):
    """承認一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[ApprovalResponse]
    total: int
