"""BulkUpdateService の具象実装（Phase 2）。

仕様ソース:
- ``.github/instructions/bulk-operation.python.instructions.md``
- ``app/common/bulk_update.py`` §プロトコル定義

L1 ルール:
- AuditLog への書き込みなしで一括 UPDATE を実行禁止
  → 各チャンクのコミット直前に構造化ログで監査記録を残す
  → TODO(domain): AuditLog DB テーブルが整備され次第 DB 書き込みに切り替えること
- 1 リクエストあたり 1000 件超を受け付けることを禁止
- 1 トランザクションあたり 50 件（BULK_BATCH_SIZE）単位でコミット分割する

対応エンティティ:
- "Task" → TicketOrm（tickets テーブル）
  更新可能フィールド: status / priority / assignee_id / due_date / done_ratio / subject
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.bulk_update import (
    BULK_BATCH_SIZE,
    BULK_REQUEST_MAX_ITEMS,
    BulkUpdateItem,
    BulkUpdateResult,
)
from app.common.bulk_operation.constants import BulkOperationStatus
from app.common.logger import get_logger
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.models.ticket import TicketOrm

logger = get_logger(component="common.bulk_update_service")

# 一括更新で許可するエンティティタイプ（拡張時はここに追加する）
_SUPPORTED_ENTITY_TYPES: frozenset[str] = frozenset({"Task"})

# Task エンティティで更新可能なフィールド（許可リスト方式: 意図しないフィールド書き換えを防止）
_TASK_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"status", "priority", "assignee_id", "due_date", "done_ratio", "subject"}
)


class BulkUpdateServiceImpl:
    """BulkUpdateService の具象実装。

    エンティティタイプ "Task"（TicketOrm）の一括更新をサポートする。
    BULK_BATCH_SIZE 件単位でトランザクションを分割してコミットする。
    """

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()

    async def bulk_update(
        self,
        items: list[BulkUpdateItem],
        user_id: str,
    ) -> Result[BulkUpdateResult]:
        """一括更新を実行する。

        Args:
            items: 更新対象リスト。1000 件以内（L1 上限）。
            user_id: 操作ユーザー ID（監査ログ用）。

        Returns:
            Ok(BulkUpdateResult): 成功・失敗件数と操作 ID。
            Err(AppError): L1 違反（1000 件超）または内部エラー。
        """
        # --- L1: 件数上限チェック ---
        if len(items) > BULK_REQUEST_MAX_ITEMS:
            return Err(AppError(
                type="VALIDATION",
                message=f"一括更新の上限は {BULK_REQUEST_MAX_ITEMS} 件です。{len(items)} 件が渡されました。",
            ))

        # --- L2: 100 件超の事前警告ログ ---
        if len(items) > 100:
            logger.warning(
                "bulk_update.large_request",
                count=len(items),
                user_id=user_id,
                note="L2: 100件超のリクエストは処理負荷が高くなります",
            )

        operation_id = str(uuid.uuid4())
        success_count = 0
        failed_count = 0

        logger.info(
            "bulk_update.started",
            operation_id=operation_id,
            total=len(items),
            user_id=user_id,
        )

        # --- エンティティタイプ検証 ---
        for item in items:
            if item.entity_type not in _SUPPORTED_ENTITY_TYPES:
                return Err(AppError(
                    type="VALIDATION",
                    message=f"未対応のエンティティタイプ: {item.entity_type}。対応: {sorted(_SUPPORTED_ENTITY_TYPES)}",
                ))

        # --- BULK_BATCH_SIZE 件単位でチャンク分割して処理 ---
        for chunk_start in range(0, len(items), BULK_BATCH_SIZE):
            chunk = items[chunk_start : chunk_start + BULK_BATCH_SIZE]
            chunk_success, chunk_failed = await self._process_chunk(chunk, user_id, operation_id)
            success_count += chunk_success
            failed_count += chunk_failed

        final_status = (
            BulkOperationStatus.COMPLETED
            if failed_count == 0
            else BulkOperationStatus.PARTIAL_FAILED
        )

        logger.info(
            "bulk_update.completed",
            operation_id=operation_id,
            success_count=success_count,
            failed_count=failed_count,
            status=final_status,
            user_id=user_id,
        )

        return Ok(BulkUpdateResult(
            operation_id=operation_id,
            success_count=success_count,
            failed_count=failed_count,
            status=final_status,
        ))

    async def _process_chunk(
        self,
        chunk: list[BulkUpdateItem],
        user_id: str,
        operation_id: str,
    ) -> tuple[int, int]:
        """1 チャンク（最大 BULK_BATCH_SIZE 件）を 1 トランザクションで処理する。

        Returns:
            (success_count, failed_count) のタプル。
        """
        success_count = 0
        failed_count = 0
        now = self._clock.now()

        try:
            for item in chunk:
                result = await self._update_entity(item, now)
                if result:
                    success_count += 1
                else:
                    failed_count += 1

            # L1: AuditLog への書き込み（現状は構造化ログ。DB テーブル整備後に切り替えること）
            # TODO(domain): AuditLog DB テーブルが整備され次第、ここで DB 書き込みに切り替える
            logger.info(
                "audit.bulk_update",
                operation_id=operation_id,
                user_id=user_id,
                chunk_success=success_count,
                chunk_failed=failed_count,
                entity_ids=[item.entity_id for item in chunk],
            )

            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            logger.error(
                "bulk_update.chunk.error",
                operation_id=operation_id,
                error=str(exc),
            )
            # チャンク全件を失敗扱い
            failed_count = len(chunk)
            success_count = 0

        return success_count, failed_count

    async def _update_entity(self, item: BulkUpdateItem, now: Any) -> bool:
        """単一エンティティを更新する。更新成功なら True、スキップ（未存在等）なら False。"""
        if item.entity_type == "Task":
            return await self._update_task(item, now)
        return False

    async def _update_task(self, item: BulkUpdateItem, now: Any) -> bool:
        """TicketOrm の 1 件を更新する。

        許可リスト外のフィールドは無視する（意図しない書き換え防止）。
        """
        try:
            ticket_id = int(item.entity_id)
        except (ValueError, TypeError):
            logger.warning("bulk_update.task.invalid_id", entity_id=item.entity_id)
            return False

        ticket = await self._session.get(TicketOrm, ticket_id)
        if ticket is None or ticket.delete_flg != 0:
            logger.warning("bulk_update.task.not_found", ticket_id=ticket_id)
            return False

        # 許可フィールドのみ更新（許可リスト方式で意図しないカラム書き換えを封じる）
        for field, value in item.data.items():
            if field in _TASK_UPDATABLE_FIELDS:
                setattr(ticket, field, value)

        ticket.updated_at = now
        return True
