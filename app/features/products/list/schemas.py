"""製品一覧 API の Pydantic スキーマ定義。

仕様ソース: docs/ 未定義（初期実装）
# TODO(domain): 正式仕様確定後にフィールド定義を見直すこと
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductItem(BaseModel):
    """製品 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="製品 ID")
    project_id: int = Field(description="所属プロジェクト ID")
    name: str = Field(description="製品名")


class ProductListResponse(BaseModel):
    """製品一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[ProductItem]
    total: int = Field(description="総件数")
