"""Result → FastAPI HTTPException 変換。

仕様ソース: ``docs/03_detail-design/01_common/common-backend.md`` §5.2

Router は Result を展開する際に必ず本関数を経由すること。各 Router に if/elif
で分岐するコードを書くことは禁止（コピペ漏れ・マッピングずれのリスク）。

セキュリティ（L1）:
- 500 レスポンスの ``detail`` にスタックトレース・クラス名・内部構造を含めない
- ``request_id`` のみを含めてトレース可能にする
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from app.core.result import AppError

# AppError.type → HTTP status code のマッピング
_STATUS_MAP: dict[str, int] = {
    "NOT_FOUND": 404,
    "VALIDATION": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "CONFLICT": 409,
    "BUSINESS_RULE": 422,
    "INTERNAL": 500,
}


def to_http_exception(error: AppError, request_id: str | None = None) -> HTTPException:
    """``AppError`` を ``HTTPException`` に変換して返す（raise はしない）。

    Router では ``raise to_http_exception(result.error, request_id)`` の形で使う。
    """
    status = _STATUS_MAP.get(error.type, 500)
    if status == 500:
        # 内部エラーはメッセージを固定。内部情報は漏らさない（L1）
        detail: dict[str, str] = {"message": "Internal server error"}
        if request_id:
            detail["request_id"] = request_id
        return HTTPException(status_code=status, detail=detail)
    return HTTPException(status_code=status, detail={"message": error.message})


def raise_http_exception(error: AppError, request_id: str | None = None) -> NoReturn:
    """``to_http_exception`` の raise 版。型上は ``NoReturn``。"""
    raise to_http_exception(error, request_id)
