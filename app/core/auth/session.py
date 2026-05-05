"""Redis-backed session middleware.

Replaces starlette-session with a minimal, project-owned implementation.
Session specification: ``docs/02_basic-design/01_common/basic-design.md`` §認証フロー

Security notes:
- Session ID is generated via ``secrets.token_urlsafe(32)`` (256-bit entropy)
- Cookie flags: HttpOnly=True, SameSite=strict, Secure=production-only
- Redis TTL is renewed on every authenticated request (sliding window)

配置方針: 認証基盤の一部として ``app/core/auth/`` に配置する。Cookie 名等の
定数は ``app.core.constants.session`` に分離し、WebSocket / IIS 認証からは
定数ファイルのみを import することで循環依存を回避する。
"""

from __future__ import annotations

import json
import secrets
from typing import TypedDict

import redis.asyncio as aioredis
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants.session import COOKIE_NAME, REDIS_KEY_PREFIX, SESSION_ID_BYTES

logger = structlog.get_logger(__name__)

__all__ = [
    "COOKIE_NAME",
    "REDIS_KEY_PREFIX",
    "SESSION_ID_BYTES",
    "SessionData",
    "SessionMiddleware",
    "destroy_session",
]


class SessionData(TypedDict):
    """セッションに保存するデータ構造（basic-design.md §認証フロー 準拠）."""

    user_id: str  # User.id (UUID v7)
    login_id: str  # Windows sAMAccountName
    department_id: str  # User.department_id (UUID v7)
    authenticated_at: int  # Unix タイムスタンプ（ミリ秒）


class SessionMiddleware(BaseHTTPMiddleware):
    """Redis セッション Middleware.

    Request 前処理:
      Cookie から session_id を取得 → Redis から SessionData をロード
      → ``request.state.session`` にセット（存在しない場合は空 dict）

    Response 後処理:
      ``request.state.session`` が変更された場合 → Redis に書き込み + Cookie セット
      ``request.state._session_destroyed`` が True の場合 → Redis 削除 + Cookie クリア
    """

    # TODO(security): セッション固定攻撃 - requires review before merge
    # TODO(security): Cookie 窃取（XSS 経由） - requires review before merge

    def __init__(
        self,
        app: object,
        redis_client: aioredis.Redis,
        max_age: int = 28800,
        is_secure: bool = False,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._redis = redis_client
        self._max_age = max_age
        self._is_secure = is_secure

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """リクエスト前後でセッションの読み込み・書き込みを行う."""
        session_id = request.cookies.get(COOKIE_NAME)
        session_data: dict[str, str | int] = {}
        is_existing_session = False

        # --- Request 前処理: Redis からセッション取得 ---
        if session_id:
            raw = await self._redis.get(f"{REDIS_KEY_PREFIX}{session_id}")
            if raw is not None:
                session_data = json.loads(raw)
                is_existing_session = True
            else:
                # Cookie はあるが Redis にセッションが無い（期限切れ等）
                session_id = None
                logger.info("session_expired_or_missing", cookie_present=True)

        request.state.session = session_data
        request.state._session_destroyed = False

        response: Response = await call_next(request)  # type: ignore[operator]

        # --- Response 後処理 ---
        if getattr(request.state, "_session_destroyed", False):
            # セッション破棄
            if session_id:
                await self._redis.delete(f"{REDIS_KEY_PREFIX}{session_id}")
                logger.info("session_destroyed")
            self._clear_cookie(response)
            return response

        current_session: dict[str, str | int] = getattr(request.state, "session", {})

        if current_session:
            if not is_existing_session or current_session != session_data:
                # 新規セッション or 変更あり → Redis に書き込み
                if not session_id:
                    session_id = secrets.token_urlsafe(SESSION_ID_BYTES)
                await self._redis.setex(
                    f"{REDIS_KEY_PREFIX}{session_id}",
                    self._max_age,
                    json.dumps(current_session),
                )
                self._set_cookie(response, session_id)
                logger.info("session_created_or_updated", is_new=not is_existing_session)
            elif is_existing_session:
                # 変更なし → TTL のみリフレッシュ（sliding window）
                await self._redis.expire(
                    f"{REDIS_KEY_PREFIX}{session_id}",
                    self._max_age,
                )

        return response

    def _set_cookie(self, response: Response, session_id: str) -> None:
        """セッション Cookie をセットする."""
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_id,
            max_age=self._max_age,
            httponly=True,
            secure=self._is_secure,
            samesite="strict",
            path="/",
        )

    def _clear_cookie(self, response: Response) -> None:
        """セッション Cookie を削除する."""
        response.delete_cookie(
            key=COOKIE_NAME,
            httponly=True,
            secure=self._is_secure,
            samesite="strict",
            path="/",
        )


def destroy_session(request: Request) -> None:
    """セッションを破棄するヘルパー.

    Usage::

        from app.core.auth.session import destroy_session

        @router.post("/logout")
        async def logout(request: Request) -> dict[str, str]:
            destroy_session(request)
            return {"status": "ok"}
    """
    request.state._session_destroyed = True
    request.state.session = {}
