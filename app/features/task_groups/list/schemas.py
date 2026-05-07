"""タスクグループ API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- 埋め込み型 -----------------------------------------------------------


class GroupMemberSummary(BaseModel):
    """グループメンバーのサマリー（チケット ID + 題名 + ステータス）。"""

    model_config = ConfigDict(from_attributes=True)

    ticket_id: int = Field(description="チケット ID")
    subject: str = Field(description="チケット題名")
    status: str = Field(description="チケットステータス")
    product_name: str = Field(description="所属製品名")
    added_at: str = Field(description="グループ追加日時 (ISO 8601)")


# ---- レスポンス -----------------------------------------------------------


class TaskGroupItem(BaseModel):
    """タスクグループ 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="グループ ID")
    name: str = Field(description="グループ名")
    description: str | None = Field(default=None, description="グループ説明")
    member_count: int = Field(description="メンバー数（論理削除済みチケットを除く）")
    members: list[GroupMemberSummary] = Field(description="メンバー一覧")


class TaskGroupListResponse(BaseModel):
    """タスクグループ一覧レスポンス。"""

    items: list[TaskGroupItem]
    total: int = Field(description="総件数")


class TaskGroupCreateResponse(BaseModel):
    """タスクグループ作成レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    members: list[GroupMemberSummary] = Field(default_factory=list)


# ---- リクエスト -----------------------------------------------------------


class TaskGroupCreateRequest(BaseModel):
    """タスクグループ作成リクエスト。

    ticket_ids に指定したチケットをまとめてグループ化する。
    既に別グループに属しているチケットも追加可能（1 チケット複数グループ対応）。
    """

    name: str = Field(min_length=1, max_length=200, description="グループ名（例: OS v2 移行作業）")
    description: str | None = Field(default=None, max_length=1000, description="グループ説明（任意）")
    ticket_ids: list[int] = Field(
        min_length=2,
        description="グループ化するチケット ID リスト（2 件以上必須）",
    )


class TaskGroupUpdateRequest(BaseModel):
    """タスクグループ更新リクエスト（名前・説明のみ変更可。メンバー変更は別エンドポイント）。"""

    name: str = Field(min_length=1, max_length=200, description="グループ名")
    description: str | None = Field(default=None, max_length=1000, description="グループ説明")


class TaskGroupAddMembersRequest(BaseModel):
    """グループへのチケット追加リクエスト。"""

    ticket_ids: list[int] = Field(min_length=1, description="追加するチケット ID リスト")


class TaskGroupRemoveMembersRequest(BaseModel):
    """グループからのチケット削除リクエスト。"""

    ticket_ids: list[int] = Field(min_length=1, description="削除するチケット ID リスト")
