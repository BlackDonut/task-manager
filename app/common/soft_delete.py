"""論理削除ペイロード生成。

仕様ソース: ``docs/03_detail-design/01_common/common-backend.md`` §5.3

- 削除時は ``soft_delete_payload`` で ``delete_flg / updated_at / updated_by_id`` を一括更新
- フィルタロジックは DB レイヤー実装時に追加する
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from app.core.clock import Clock


class SoftDeletePayload(TypedDict):
    """論理削除実行時の UPDATE 対象カラム。"""

    delete_flg: int
    updated_at: datetime
    updated_by_id: str


def soft_delete_payload(clock: Clock, user_id: str) -> SoftDeletePayload:
    """論理削除実行時の UPDATE ペイロードを生成する。"""
    return {
        "delete_flg": 1,
        "updated_at": clock.now(),
        "updated_by_id": user_id,
    }
