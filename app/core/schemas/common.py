"""共通スキーマ（ID・日付・ソート・offset ページネーション）。

各機能の ``schemas.py`` でこれらを import して使用すること。同等型の独自実装禁止。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- ページネーション系定数（全 API で共通） ---
# 1 ページ最大件数は N+1・メモリ爆発・レスポンス肥大の抑制のため 100 件
MAX_PAGE_SIZE: int = 100
DEFAULT_PAGE_SIZE: int = 20

type SortOrder = Literal["asc", "desc"]


class IdParamSchema(BaseModel):  # type: ignore[explicit-any]
    """パスパラメータの UUID バリデーション。

    業務上の識別子は UUID v7 を利用するが、バリデーションは UUID 形式（v4 含む）で行う。
    """

    id: str = Field(..., min_length=32, max_length=36, pattern=r"^[0-9a-fA-F-]{32,36}$")


class OffsetPaginationParams(BaseModel):  # type: ignore[explicit-any]
    """offset ベースのページネーションクエリパラメータ。

    カーソルページネーションが基本（L2）。offset は小規模一覧・管理画面のみで利用。
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class TimestampedResponse(BaseModel):  # type: ignore[explicit-any]
    """``created_at`` / ``updated_at`` を持つレスポンスの共通基底。"""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
