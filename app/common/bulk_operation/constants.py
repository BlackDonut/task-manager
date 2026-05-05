"""BulkOperation 関連の Enum 定数（TBL-011）。"""

from __future__ import annotations

from enum import StrEnum


class BulkOperationStatus(StrEnum):
    """一括操作ステータス（TBL-011 §status）。

    遷移: PENDING → IN_PROGRESS → COMPLETED / PARTIAL_FAILED / ROLLED_BACK
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    ROLLED_BACK = "ROLLED_BACK"
