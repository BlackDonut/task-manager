"""開発環境用の認証バイパスミドルウェア。

# TODO(security): 本番環境では絶対に有効化しない - requires review before check-in
# - 脅威モデル: docs/02_basic-design/01_common/basic-design.md §認証バイパス

app_env == "development" でのみ有効化される。全リクエストに対して
``request.state.user`` にフォールバック開発ユーザーを設定する。
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.common.logger import get_logger
from app.core.auth.models import AuthenticatedUser

logger = get_logger(component="dev_auth")

# 開発環境用フォールバックユーザー（全権限）
_FALLBACK_DEV_USER = AuthenticatedUser(
    id="00000000-0000-0000-0000-000000000001",
    login_id="dev-admin",
    department_id="00000000-0000-0000-0000-000000000001",
    is_sys_admin=True,
    permissions=(),
)


class DevAuthMiddleware(BaseHTTPMiddleware):
    """開発環境専用: 全リクエストに認証済みユーザーを自動設定する。"""

    def __init__(self, app: object, dev_login_id: str = "dev-admin") -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._dev_login_id = dev_login_id

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """request.state.user が未設定の場合に開発ユーザーを注入する。"""
        if not hasattr(request.state, "user") or request.state.user is None:
            request.state.user = _FALLBACK_DEV_USER
            logger.info("dev_auth.using_fallback", login_id=self._dev_login_id)

        response: Response = await call_next(request)  # type: ignore[operator]
        return response
