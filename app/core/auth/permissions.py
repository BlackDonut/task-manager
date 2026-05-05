"""RBAC / ABAC の権限判定（純粋関数）。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md`` §11.6

判定関数は副作用なしの純粋関数として切り出し、Depends から独立させる。
これによりユニットテストで RBAC / ABAC の真理値表を網羅的に検証できる。
"""

from __future__ import annotations

from app.core.auth.models import AuthenticatedUser, PermissionRef
from app.core.constants.permissions import Actions, Resources
from app.core.types.permission_condition import (
    FieldMatch,
    OrganizationSubtree,
    OwnerOnly,
    PermissionCondition,
    SameOrganization,
)


class AbacContext:
    """ABAC 条件評価に必要な対象リソースの属性。

    OWNER_ONLY / SAME_ORGANIZATION / FIELD_MATCH で参照される。
    リソースを持たないエンドポイント（一覧取得等）では None を渡してよい。
    """

    def __init__(
        self,
        *,
        resource_owner_id: str | None = None,
        resource_department_id: str | None = None,
        resource_ancestor_department_ids: tuple[str, ...] = (),
        resource_fields: dict[str, object] | None = None,
    ) -> None:
        self.owner_id = resource_owner_id
        self.department_id = resource_department_id
        self.ancestor_department_ids = resource_ancestor_department_ids
        self.fields = resource_fields or {}


def _match_action_resource(p: PermissionRef, action: Actions, resource: Resources) -> bool:
    return p.action == action and p.resource == resource


def _evaluate_condition(
    condition: PermissionCondition,
    user: AuthenticatedUser,
    ctx: AbacContext | None,
) -> bool:
    """ABAC 条件を評価する。

    リソース属性が与えられていない（ctx is None）のに条件が課されている場合は
    安全側に倒して False を返す（fail closed）。
    """
    if isinstance(condition, OwnerOnly):
        return ctx is not None and ctx.owner_id == user.id
    if isinstance(condition, SameOrganization):
        return ctx is not None and ctx.department_id == user.department_id
    if isinstance(condition, OrganizationSubtree):
        return ctx is not None and user.department_id in ctx.ancestor_department_ids
    if isinstance(condition, FieldMatch):
        if ctx is None:
            return False
        expected: object = user.department_id if condition.value_from == "user.department_id" else user.id
        return ctx.fields.get(condition.field) == expected
    # 網羅漏れは型で検出されるが、実行時も安全側に倒す
    return False


def has_permission(
    user: AuthenticatedUser,
    action: Actions,
    resource: Resources,
    ctx: AbacContext | None = None,
) -> bool:
    """ユーザーが指定 Action / Resource を実行可能か判定する。

    SystemAdmin はバイパス。それ以外は Permission を走査し、ABAC 条件も評価する。
    """
    if user.is_sys_admin:
        return True
    for p in user.permissions:
        if not _match_action_resource(p, action, resource):
            continue
        if p.condition is None:
            return True
        if _evaluate_condition(p.condition, user, ctx):
            return True
    return False
