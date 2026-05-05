"""IIS Windows 認証ミドルウェア。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md`` §11.2

処理フロー:
1. IIS の ``X-IIS-WindowsAuth-User`` ヘッダーから ``login_id`` を取得
2. Redis セッションに既存セッションがあれば再利用（sliding window）
3. セッションなし → ``load_authenticated_user()`` で DB から User 情報を取得
4. LDAP 有効時 → アカウント有効性を確認（``ldap_adapter.verify_account``）
5. ``request.state.user`` に ``AuthenticatedUser`` を設定
6. Redis セッションを生成/更新

# TODO(security): IIS リバースプロキシの X-Forwarded ヘッダー偽造対策
# - requires review before check-in
# - 脅威モデル: docs/02_basic-design/01_common/basic-design.md §セッション偽装
# IIS のみが本ヘッダーを設定できる前提。AP サーバーへの直接アクセスは
# ネットワークレベルで遮断する（docs/guides/network-architecture.md 参照）。
"""

from __future__ import annotations

import json

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.auth.models import AuthenticatedUser
from app.core.constants.session import COOKIE_NAME, REDIS_KEY_PREFIX

logger = structlog.get_logger(__name__)

# IIS が設定する Windows 認証ヘッダー名
IIS_AUTH_HEADER = "X-IIS-WindowsAuth-User"

# 認証不要のパス（ヘルスチェック・OpenAPI 等）
_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/healthz",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
    }
)


class IISAuthMiddleware(BaseHTTPMiddleware):
    """IIS Windows 認証 → DB/LDAP → Redis セッション → request.state.user の一連フロー。

    # TODO(security): 本番投入前に以下を確認すること - requires review before check-in
    # - IIS → AP 間のネットワーク制限（直接アクセスの遮断）
    # - X-IIS-WindowsAuth-User ヘッダーの偽造不可能性
    """

    def __init__(
        self,
        app: object,
        *,
        redis_client: object,
        ldap_adapter: object | None = None,
        session_max_age: int = 28800,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._redis = redis_client
        self._ldap = ldap_adapter
        self._session_max_age = session_max_age

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # 公開パスはスキップ
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)  # type: ignore[no-any-return, operator]

        # 1. IIS ヘッダーから login_id を取得
        login_id = request.headers.get(IIS_AUTH_HEADER)
        if not login_id:
            logger.warning("iis_auth.missing_header", path=request.url.path)
            return JSONResponse(
                status_code=401,
                content={"message": "Unauthenticated"},
            )

        # DOMAIN\\user → user に正規化
        if "\\" in login_id:
            login_id = login_id.split("\\", 1)[1]

        # 2. Redis セッションを確認
        user = await self._try_restore_session(request, login_id)
        if user is not None:
            request.state.user = user
            return await call_next(request)  # type: ignore[no-any-return, operator]

        # 3. DB からユーザーをロード
        user = self._load_from_db(login_id)
        if user is None:
            logger.warning("iis_auth.user_not_found", login_id_length=len(login_id))
            return JSONResponse(
                status_code=401,
                content={"message": "Unauthenticated"},
            )

        # 4. LDAP でアカウント有効性を確認（有効時のみ）
        if self._ldap is not None:
            is_valid = self._ldap.verify_account(login_id)  # type: ignore[attr-defined]
            if not is_valid:
                logger.warning("iis_auth.ldap_account_invalid", user_id=user.id)
                return JSONResponse(
                    status_code=401,
                    content={"message": "Account disabled"},
                )

        # 5. request.state.user を設定
        request.state.user = user

        # 6. Redis セッションを生成
        response: Response = await call_next(request)  # type: ignore[operator]
        await self._create_session(request, user)
        return response

    async def _try_restore_session(
        self,
        request: Request,
        login_id: str,
    ) -> AuthenticatedUser | None:
        """Redis セッションからユーザー情報を復元する。"""
        session_id = request.cookies.get(COOKIE_NAME)
        if not session_id:
            return None

        raw = await self._redis.get(f"{REDIS_KEY_PREFIX}{session_id}")  # type: ignore[attr-defined]
        if raw is None:
            return None

        data = json.loads(raw)
        if data.get("login_id") != login_id:
            # セッションと IIS ヘッダーのユーザーが不一致（セッション偽装の可能性）
            logger.warning("iis_auth.session_mismatch", session_login=data.get("login_id"))
            await self._redis.delete(f"{REDIS_KEY_PREFIX}{session_id}")  # type: ignore[attr-defined]
            return None

        # sliding window: TTL を延長
        await self._redis.expire(f"{REDIS_KEY_PREFIX}{session_id}", self._session_max_age)  # type: ignore[attr-defined]

        # セッションから AuthenticatedUser を再構築するため DB ロードが必要
        return self._load_from_db(login_id)

    def _load_from_db(self, login_id: str) -> AuthenticatedUser | None:
        # TODO(domain): SQLAlchemy 削除に伴いユーザーロード実装が必要。
        # 新しいユーザーリポジトリ層が整備されるまで None を返す。
        return None

    async def _create_session(self, request: Request, user: AuthenticatedUser) -> None:
        """Redis セッションを新規作成する。"""
        import secrets
        import time

        session_id = secrets.token_urlsafe(32)
        session_data = json.dumps(
            {
                "user_id": user.id,
                "login_id": user.login_id,
                "department_id": user.department_id,
                "authenticated_at": int(time.time()),
            }
        )
        await self._redis.setex(  # type: ignore[attr-defined]
            f"{REDIS_KEY_PREFIX}{session_id}",
            self._session_max_age,
            session_data,
        )
        # Cookie はレスポンスミドルウェア（SessionMiddleware）で管理するため
        # ここでは request.state に保存して SessionMiddleware に委譲
        request.state.session = {
            "user_id": user.id,
            "login_id": user.login_id,
            "department_id": user.department_id,
        }
