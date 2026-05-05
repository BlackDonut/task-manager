---
name: batch-processing
description: "バッチ処理の実装パターン：冪等性・リトライ・タイムアウト・トランザクション境界・ログ・エラー通知・テスト追加。バッチジョブの新規実装・バッチの認可対応・バッチ処理のレビュー時に使用する。"
applyTo: "app/batch/**/*.py"
---

# Batch Processing Skill

基本ルールは `batch.python.instructions.md` を参照。

---

## バッチ共通型

```python
# app/batch/types.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BatchError:
    record_id: str  # 不透明 ID
    error_type: str
    message: str  # PII 禁止


@dataclass
class BatchResult:
    batch_name: str
    started_at: datetime  # Clock ファクトリ経由
    finished_at: datetime
    status: str  # "SUCCESS" | "PARTIAL_FAILURE" | "FAILURE"
    processed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    errors: list[BatchError] = field(default_factory=list)
```

---

## 冪等性（必須）

複数回実行しても同じ結果になること。

```python
# NG: 処理済みでも再実行される
stmt = select(Task).where(Task.status == "OPEN")

# OK: 未処理のみ（冪等性保証）
stmt = select(Task).where(
    Task.status == "OPEN",
    Task.notified_at.is_(None),
    Task.delete_flg == 0,
)
```

---

## トランザクション境界

全件を 1 トランザクションにしない。レコードまたは小バッチ単位でコミット。

```python
# NG: 全件 1 トランザクション
with session.begin():
    for task in tasks:
        task.is_delayed = True

# OK: 1 件ずつ、失敗を記録して継続
errors: list[BatchError] = []
for task in tasks:
    try:
        with session.begin():
            task.is_delayed = True
            task.delay_detected_at = clock.now()
            session.add(task)
        processed_count += 1
    except Exception as e:
        errors.append(BatchError(
            record_id=task.id,
            error_type="UPDATE_FAILED",
            message=str(e),
        ))
        failed_count += 1
```

---

## タイムアウトとリトライ

```python
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

BATCH_TIMEOUT_SEC = 10 * 60  # ASSUMPTION: 10 分

async def with_retry(
    fn: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
) -> T:
    """最大 max_attempts 回・指数バックオフでリトライ。"""
    for attempt in range(max_attempts):
        try:
            return await fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(0.1 * (2 ** attempt))
    raise RuntimeError("Unreachable")
```

---

## ログ出力（必須）

開始・終了・各レコード結果を構造化ログで記録。

```python
import structlog

logger = structlog.get_logger()

logger.info("バッチ開始", batch_name=batch_name, started_at=started_at.isoformat())
logger.info(
    "バッチ完了",
    batch_name=batch_name,
    status=status,
    processed_count=processed_count,
    failed_count=failed_count,
    skipped_count=skipped_count,
    duration_ms=duration_ms,
)
logger.error(
    "レコード処理失敗",
    batch_name=batch_name,
    record_id=task.id,
    error_type="UPDATE_FAILED",
)
```

---

## バッチ実行テンプレート

```python
# batch/runners/deadline_check.py
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.batch.types import BatchError, BatchResult
from app.clock import Clock
from app.db.models.task import Task

logger = structlog.get_logger()


class DeadlineCheckBatch:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def execute(self) -> BatchResult:
        batch_name = "deadline-check"
        started_at = self._clock.now()
        errors: list[BatchError] = []
        processed_count = 0
        failed_count = 0
        skipped_count = 0

        # 未処理のみ（冪等性）
        stmt = select(Task).where(
            Task.due_date < started_at,
            Task.is_delayed.is_(False),
            Task.delete_flg == 0,
        )
        result = self._session.execute(stmt)
        tasks = result.scalars().all()

        for task in tasks:
            try:
                with self._session.begin_nested():
                    task.is_delayed = True
                    task.delay_detected_at = started_at
                    self._session.add(task)
                processed_count += 1
            except Exception as e:
                errors.append(BatchError(
                    record_id=task.id,
                    error_type="UPDATE_FAILED",
                    message=str(e),
                ))
                failed_count += 1

        self._session.commit()

        status = (
            "SUCCESS" if failed_count == 0
            else "PARTIAL_FAILURE" if processed_count > 0
            else "FAILURE"
        )

        return BatchResult(
            batch_name=batch_name,
            started_at=started_at,
            finished_at=self._clock.now(),
            status=status,
            processed_count=processed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            errors=errors,
        )
```
