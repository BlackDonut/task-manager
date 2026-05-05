"""認証済みユーザー・組織スコープ・権限参照の型定義。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md`` §11.6
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from app.core.constants.permissions import Actions, Resources
from app.core.types.permission_condition import PermissionCondition


class OrganizationScope(TypedDict):
    """全 Repository メソッドで必須のデータスコープ（L1）。"""

    organization_id: str  # user.department_id
    is_sys_admin: bool


@dataclass(frozen=True, slots=True)
class PermissionRef:
    """ユーザーが保有する 1 件の Permission。"""

    action: Actions
    resource: Resources
    condition: PermissionCondition | None = None


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """認証済みユーザー情報。

    PII（氏名・メール）は保持しない。``login_id`` は Windows sAMAccountName で
    PII 性が低いが、ログ出力時はハッシュ化するか ``user_id`` のみを出すこと（L1）。
    """

    id: str
    login_id: str
    department_id: str
    is_sys_admin: bool
    permissions: tuple[PermissionRef, ...] = field(default_factory=tuple)

    @property
    def scope(self) -> OrganizationScope:
        """Repository に渡す ``OrganizationScope`` を生成する。"""
        return {
            "organization_id": self.department_id,
            "is_sys_admin": self.is_sys_admin,
        }
