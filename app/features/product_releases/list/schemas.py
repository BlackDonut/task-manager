"""製品作業サイクル API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---- 定数 ---------------------------------------------------------------
# co-change: frontend/src/api/endpoints/types.ts ReleaseType / ReleaseStatus

ReleaseType = Literal[
    "initial",          # 初回リリース
    "spec_change",      # 仕様変更
    "version_upgrade",  # バージョンアップ（OS・基盤等）
    "maintenance",      # 保守
]

ReleaseStatus = Literal[
    "planning",     # 計画中
    "in_progress",  # 進行中
    "completed",    # 完了
]

# ---- レスポンス -----------------------------------------------------------


class ProductReleaseItem(BaseModel):
    """製品作業サイクル 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="リリース ID")
    product_id: int = Field(description="所属製品 ID")
    name: str = Field(description="サイクル名（例: v1.0 初回リリース）")
    release_type: ReleaseType = Field(description="種別: initial / spec_change / version_upgrade / maintenance")
    status: ReleaseStatus = Field(description="進捗: planning / in_progress / completed")
    target_date: str | None = Field(default=None, description="目標完了日 (YYYY-MM-DD)。未設定の場合は null")


class ProductReleaseListResponse(BaseModel):
    """製品作業サイクル一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[ProductReleaseItem]
    total: int = Field(description="総件数")


# ---- リクエスト -----------------------------------------------------------


class ProductReleaseCreateRequest(BaseModel):
    """製品作業サイクル作成リクエスト。"""

    product_id: int = Field(description="所属製品 ID")
    name: str = Field(min_length=1, max_length=200, description="サイクル名")
    release_type: ReleaseType = Field(default="initial", description="種別")
    status: ReleaseStatus = Field(default="planning", description="進捗")
    target_date: str | None = Field(
        default=None,
        description="目標完了日 (YYYY-MM-DD)。未設定の場合は null",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )


class ProductReleaseUpdateRequest(BaseModel):
    """製品作業サイクル更新リクエスト。product_id は変更不可。"""

    name: str = Field(min_length=1, max_length=200, description="サイクル名")
    release_type: ReleaseType = Field(description="種別")
    status: ReleaseStatus = Field(description="進捗")
    target_date: str | None = Field(
        default=None,
        description="目標完了日 (YYYY-MM-DD)。未設定の場合は null",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
