"""グローバル例外ハンドラ登録。

L1: エラーレスポンスにスタックトレース・内部情報を含めない。

- FastAPI の ``HTTPException`` はそのまま通す
- ``AppError`` を外部に raise した場合（L2 違反）もここで 500 に丸める
- その他の未捕捉例外は ``{"message": "Internal server error", "request_id": ...}`` で返す
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.logger import get_logger


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI アプリに共通例外ハンドラを登録する。"""
    log = get_logger(component="error_handler")

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # 入力バリデーションエラーは安全に返す（422 → 400 相当の扱い。ただし詳細は制限）
        log.info("validation_error", path=request.url.path, errors=exc.errors())
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid request parameters"},
        )

    @app.exception_handler(Exception)
    async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        # exc_info=True でサーバログにはトレースを残すが、レスポンスには含めない（L1）
        log.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error",
                "request_id": request_id,
            },
        )
