"""一括更新基盤のインターフェース定義。

仕様ソース:
- ``docs/03_detail-design/01_common/common-backend.md`` §5.9
- ``.github/instructions/bulk-operation.instructions.md``

- AuditLog 書き込みなしの一括更新は L1 違反
- 1 トランザクションあたり ``BULK_BATCH_SIZE`` 件単位でコミット分割する
- 1 リクエストあたり 1000 件を超える items を ``bulk_update`` に渡すことは L1 違反

Phase 2 実装: ``app/common/services/bulk_update_service.py`` の ``BulkUpdateServiceImpl``
  - 対応エンティティ: "Task"（TicketOrm）
  - 使用方法:
      service = BulkUpdateServiceImpl(session)
      result = await service.bulk_update(items, user_id)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.common.bulk_operation.constants import BulkOperationStatus
from app.core.result import Result

# 1 トランザクションあたりの最大更新件数
BULK_BATCH_SIZE: int = 50

# 1 リクエストあたりの上限件数（L1: chunking 必須の閾値）
BULK_REQUEST_MAX_ITEMS: int = 1000


@dataclass(frozen=True, slots=True)
class BulkUpdateItem:
    """一括更新の 1 要素。"""

    entity_type: str  # "Task" | "Application" 等（Resources と対応）
    entity_id: str
    data: dict[str, object]


@dataclass(frozen=True, slots=True)
class BulkUpdateResult:
    """一括更新の実行結果。"""

    operation_id: str  # BulkOperation.id と同値（AuditLog への紐付けキー）
    success_count: int
    failed_count: int
    status: BulkOperationStatus


class BulkUpdateService(Protocol):
    """一括更新サービスのインターフェース。

    実装クラスは Phase 2 以降で ``app/common/services/`` に配置予定。
    """

    async def bulk_update(
        self,
        items: list[BulkUpdateItem],
        user_id: str,
    ) -> Result[BulkUpdateResult]: ...
