"""Clock ファクトリ。

``datetime.now()`` の直接呼び出しを禁止し（L2 警告）、時刻依存ロジックを
テストで ``FixedClock`` に差し替え可能にする。

仕様ソース: ``docs/03_detail-design/01_common/common-backend.md`` §5.1

使用例::

    from app.core.clock import Clock, SystemClock

    class TasksService(BaseService):
        def __init__(self, clock: Clock) -> None:
            super().__init__(clock)

        def make(self) -> Task:
            return Task(created_at=self._clock.now())
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """現在時刻取得の抽象。タイムゾーンは UTC を返すこと。"""

    def now(self) -> datetime: ...


class SystemClock:
    """本番用の Clock。常に UTC の現在時刻を返す。"""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class FixedClock:
    """テスト用の Clock。初期化時刻を常に返す。"""

    def __init__(self, fixed_time: datetime) -> None:
        # tz-aware 強制（naive datetime を混入させないための防御）
        if fixed_time.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time


def get_clock() -> Clock:
    """FastAPI の ``Depends`` 経由で ``SystemClock`` を提供する。"""
    return SystemClock()
