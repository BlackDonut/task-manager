"""認証・認可の FastAPI Depends。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md``

セキュリティ（L1）:
- 保護エンドポイントには ``permission_required(...)`` を必ず付与する
- 認可バイパスエンドポイントは ``# TODO(security):`` + ADR + セキュリティレビュー必須

Phase 1 実装状況:
- ``get_current_user`` は IIS/LDAP/Redis 連携未実装。テスト用に
  ``app.dependency_overrides[get_current_user]`` で差し替える前提
- 本番投入前に ``# TODO(security):`` のある箇所を全て解決すること
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.auth.models import AuthenticatedUser
from app.core.auth.permissions import AbacContext, has_permission
from app.core.constants.permissions import Actions, Resources


def get_current_user(request: Request) -> AuthenticatedUser:
    """認証済みユーザーを返す Depends。

    # TODO(security): IIS ヘッダー解決 + LDAP 検証 + Redis セッション read
    - requires review before check-in
    - 脅威モデル: docs/02_basic-design/01_common/basic-design.md §セッション偽装 / LDAP 経路
    - 連携仕様: docs/03_detail-design/01_common/auth-design.md §11.2

    現状は ``request.state.user`` を参照する。ミドルウェアで設定されていない場合は
    401 を返す（fail closed）。テストでは ``dependency_overrides`` で直接差し替える。
    """
    user = getattr(request.state, "user", None)
    if not isinstance(user, AuthenticatedUser):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "Unauthenticated"})
    return user


def permission_required(action: Actions, resource: Resources) -> Depends:  # type: ignore[valid-type]
    """指定 Action / Resource を要求する Depends ファクトリ。

    ABAC 条件（OWNER_ONLY 等）が必要なエンドポイントは Service 層で追加チェック
    する（リソース取得後でないと owner_id が分からないため）。本 Depends は
    「ロール起点のゲート」のみを担う。
    """

    def _checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if has_permission(user, action, resource, ctx=None) or user.is_sys_admin:
            return user
        # 403: 認証はされているが権限がない
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": f"Missing permission: {action.value} on {resource.value}"},
        )

    return Depends(_checker)  # type: ignore[no-any-return]


__all__ = [
    "AbacContext",
    "get_current_user",
    "permission_required",
]
