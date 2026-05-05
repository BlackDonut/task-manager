"""RequestId ミドルウェア。

全リクエストに ``X-Request-ID`` を付与し、``request.state.request_id`` に格納する。
structlog の ``contextvars`` にもバインドし、以降のログに自動で ``request_id`` が付く。

- クライアント送信の ``X-Request-ID`` ヘッダーを受け付ける（分散トレース連携）
- 未指定または不正な形式（UUID 以外）の場合は新規生成する
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.common.utils.id_utils import generate_request_id, is_valid_uuid

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """リクエスト毎に ``request_id`` を払い出す。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        # 外部入力は UUID 形式を強制（任意文字列を許すとログ汚染・注入のリスク）
        request_id = incoming if incoming and is_valid_uuid(incoming) else generate_request_id()

        request.state.request_id = request_id
        # 以降のログに自動で request_id が乗る
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            # リクエスト終了時に context をクリア（次リクエストへの漏れ防止）
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
