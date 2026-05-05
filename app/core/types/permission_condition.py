"""PermissionCondition 型定義（ABAC 条件）。

仕様ソース: ``docs/03_detail-design/01_common/common-functions.md`` §2.7

Permission テーブルの ``condition`` カラムに格納する JSON の型。自由記述 JSON を
禁止し、XSS / SQL インジェクション / 権限昇格の経路を型で閉じる。

新しい条件種別を追加する場合はチーム合意後に本ファイルを更新すること（L2）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ValidationError


class OwnerOnly(BaseModel):  # type: ignore[explicit-any]
    """自分が作成したリソースのみ許可（``created_by_id == 操作ユーザー ID``）。"""

    type: Literal["OWNER_ONLY"] = "OWNER_ONLY"


class SameOrganization(BaseModel):  # type: ignore[explicit-any]
    """同一部門のリソースのみ許可（``resource.department_id == user.department_id``）。"""

    type: Literal["SAME_ORGANIZATION"] = "SAME_ORGANIZATION"


class OrganizationSubtree(BaseModel):  # type: ignore[explicit-any]
    """自部門 + 配下部門のリソースを許可。

    判定は ``OrganizationCacheService.get_ancestor_ids()`` で行う（Phase 1 以降）。
    """

    type: Literal["ORGANIZATION_SUBTREE"] = "ORGANIZATION_SUBTREE"


class FieldMatch(BaseModel):  # type: ignore[explicit-any]
    """指定フィールドが操作ユーザーの属性値と一致する場合のみ許可。"""

    type: Literal["FIELD_MATCH"] = "FIELD_MATCH"
    field: str
    value_from: Literal["user.department_id", "user.id"]


type PermissionCondition = OwnerOnly | SameOrganization | OrganizationSubtree | FieldMatch


def is_permission_condition(v: object) -> bool:
    """任意の値が ``PermissionCondition`` として有効かを判定する。

    不正な JSON をデータベース投入時点で弾くためのバリデータ。Pydantic の
    ``ValidationError`` を ``False`` に吸収する。
    """
    if not isinstance(v, dict):
        return False
    t = v.get("type")
    try:
        if t == "OWNER_ONLY":
            OwnerOnly.model_validate(v)
        elif t == "SAME_ORGANIZATION":
            SameOrganization.model_validate(v)
        elif t == "ORGANIZATION_SUBTREE":
            OrganizationSubtree.model_validate(v)
        elif t == "FIELD_MATCH":
            FieldMatch.model_validate(v)
        else:
            return False
    except ValidationError:
        return False
    return True
