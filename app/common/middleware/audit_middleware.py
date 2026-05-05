"""監査ログ自動記録ミドルウェア。

仕様ソース:
- ``docs/01_requirements/folder-structure.md``
- ``docs/02_basic-design/01_common/basic-design.md`` §監査ログ

CREATE / UPDATE / DELETE の HTTP メソッドに対して、
エンドポイント・ユーザー ID・リクエスト ID を構造化ログに記録する。
PII（氏名・メール等）は記録しない（L1）。

# TODO(domain): 要確認 — AuditLog テーブルへの書き込み要件は仕様書を参照
# 現状は構造化ログ出力のみ。DB 書き込みが必要な場合は別途実装すること。
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.common.logger import get_logger

logger = get_logger(component="audit_middleware")

# 監査対象 HTTP メソッド（読み取り専用は除外）
_AUDIT_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditMiddleware(BaseHTTPMiddleware):
    """CREATE / UPDATE / DELETE 操作を構造化ログに記録するミドルウェア。

    記録する情報:
    - ``request_id``: リクエスト追跡 ID（RequestIdMiddleware が設定）
    - ``method``: HTTP メソッド
    - ``path``: リクエストパス
    - ``user_id``: 認証ユーザー ID（UUID）— PII を含む氏名・メール等は記録しない
    - ``status_code``: レスポンスステータス
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.method not in _AUDIT_METHODS:
            return await call_next(request)  # type: ignore[operator, no-any-return]

        response: Response = await call_next(request)  # type: ignore[operator]

        # PII 禁止: user_id（UUID）のみ記録。氏名・メール等は含めない（L1）
        user = getattr(request.state, "user", None)
        user_id: str | None = getattr(user, "id", None) if user is not None else None
        request_id: str | None = getattr(request.state, "request_id", None)

        logger.info(
            "audit.operation",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            status_code=response.status_code,
        )

        return response
