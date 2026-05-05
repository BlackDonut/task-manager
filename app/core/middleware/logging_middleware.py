"""アクセスログミドルウェア。

全リクエストの ``method / path / status_code / duration_ms`` を構造化ログで記録する。
PII はパスにもクエリにも含めないこと（L1）。
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.common.logger import get_logger


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """アクセスログ出力。"""

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._log = get_logger(component="access")

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # 例外は error_handler に任せるが、アクセスログだけは残す
            duration_ms = (time.perf_counter() - start) * 1000
            self._log.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        self._log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
