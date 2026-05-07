"""BulkUpdateServiceImpl のユニットテスト。

テスト方針:
- DB セッションをモックし、サービスのロジック（バリデーション・チャンク分割・Result 返却）を検証
- _update_task は DB 依存のため個別モックで差し替える
- 実際の DB 接続は行わない
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.common.bulk_operation.constants import BulkOperationStatus
from app.common.bulk_update import BULK_REQUEST_MAX_ITEMS, BulkUpdateItem, BulkUpdateResult
from app.common.services.bulk_update_service import BulkUpdateServiceImpl
from app.core.clock import FixedClock
from app.core.result import Err, Ok


def _make_item(entity_id: str = "1", data: dict | None = None) -> BulkUpdateItem:
    return BulkUpdateItem(
        entity_type="Task",
        entity_id=entity_id,
        data=data or {"status": "in_progress"},
    )


def _make_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


class TestBulkUpdateServiceImplValidation:
    """入力バリデーションのテスト（DB アクセス不要）。"""

    @pytest.mark.asyncio
    async def test_1001件超の場合VALIDATIONエラーを返す(self) -> None:
        # Arrange
        items = [_make_item(str(i)) for i in range(BULK_REQUEST_MAX_ITEMS + 1)]
        session = _make_session()
        service = BulkUpdateServiceImpl(session)

        # Act
        result = await service.bulk_update(items, user_id="user-001")

        # Assert
        assert result.ok is False
        assert result.error.type == "VALIDATION"
        assert str(BULK_REQUEST_MAX_ITEMS) in result.error.message

    @pytest.mark.asyncio
    async def test_未対応エンティティタイプの場合VALIDATIONエラーを返す(self) -> None:
        # Arrange
        unknown_item = BulkUpdateItem(
            entity_type="UnknownEntity",
            entity_id="1",
            data={"status": "done"},
        )
        session = _make_session()
        service = BulkUpdateServiceImpl(session)

        # Act
        result = await service.bulk_update([unknown_item], user_id="user-001")

        # Assert
        assert result.ok is False
        assert result.error.type == "VALIDATION"
        assert "UnknownEntity" in result.error.message

    @pytest.mark.asyncio
    async def test_空リストの場合COMPLETED_0件で返す(self) -> None:
        # Arrange
        session = _make_session()
        service = BulkUpdateServiceImpl(session)

        # Act
        result = await service.bulk_update([], user_id="user-001")

        # Assert
        assert result.ok is True
        assert isinstance(result.value, BulkUpdateResult)
        assert result.value.success_count == 0
        assert result.value.failed_count == 0
        assert result.value.status == BulkOperationStatus.COMPLETED


class TestBulkUpdateServiceImplBehavior:
    """チャンク分割・成功/失敗カウントのテスト。"""

    @pytest.mark.asyncio
    async def test_全件成功の場合COMPLETED_ステータスを返す(self) -> None:
        # Arrange
        items = [_make_item(str(i)) for i in range(3)]
        session = _make_session()
        from datetime import UTC, datetime

        clock = FixedClock(datetime(2026, 4, 19, tzinfo=UTC))
        service = BulkUpdateServiceImpl(session, clock=clock)

        # _update_task を成功するモックに差し替え
        with patch.object(service, "_update_task", new=AsyncMock(return_value=True)):
            # Act
            result = await service.bulk_update(items, user_id="user-001")

        # Assert
        assert result.ok is True
        assert result.value.success_count == 3
        assert result.value.failed_count == 0
        assert result.value.status == BulkOperationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_一部失敗の場合PARTIAL_FAILED_ステータスを返す(self) -> None:
        # Arrange
        items = [_make_item(str(i)) for i in range(3)]
        session = _make_session()
        from datetime import UTC, datetime

        clock = FixedClock(datetime(2026, 4, 19, tzinfo=UTC))
        service = BulkUpdateServiceImpl(session, clock=clock)

        # 最初の 1 件のみ成功、残りは失敗
        update_results = [True, False, False]
        call_count = 0

        async def mock_update_task(item, now):  # noqa: ANN001, ANN202
            nonlocal call_count
            ret = update_results[call_count % len(update_results)]
            call_count += 1
            return ret

        with patch.object(service, "_update_task", new=mock_update_task):
            # Act
            result = await service.bulk_update(items, user_id="user-001")

        # Assert
        assert result.ok is True
        assert result.value.success_count == 1
        assert result.value.failed_count == 2
        assert result.value.status == BulkOperationStatus.PARTIAL_FAILED

    @pytest.mark.asyncio
    async def test_operation_idがUUID形式で返される(self) -> None:
        # Arrange
        import re

        items = [_make_item("1")]
        session = _make_session()
        service = BulkUpdateServiceImpl(session)

        with patch.object(service, "_update_task", new=AsyncMock(return_value=True)):
            # Act
            result = await service.bulk_update(items, user_id="user-001")

        # Assert
        assert result.ok is True
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(result.value.operation_id) is not None
