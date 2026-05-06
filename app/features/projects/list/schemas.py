"""プロジェクト一覧 API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectItem(BaseModel):
    """プロジェクト 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="プロジェクト ID")
    name: str = Field(description="プロジェクト名")


class ProjectListResponse(BaseModel):
    """プロジェクト一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[ProjectItem]
    total: int = Field(description="総件数")
