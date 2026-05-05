---
name: monitoring
description: "可観測性・監視パターン：構造化ログのフォーマット・ログレベル基準・ヘルスチェック・アラート発報条件・バッチ監視・定期検証・ログ設定・アラート設定の実装時に使用する。"
applyTo:
    [
        "app/common/logger.py",
        "app/core/middleware/**/*.py",
        "app/common/middleware/**/*.py",
    ]
---

# Monitoring & Observability Skill

## 構造化ログフォーマット

全ログは JSON 形式（structlog 使用）。

```python
# 必須フィールド
# timestamp: UTC ISO 8601
# level: "info" | "warning" | "error"
# message: 人間が読めるメッセージ
# service: "backend" | "batch"
# request_id: リクエスト横断のトレース ID（任意）
# batch_name: バッチ名（バッチ処理の場合、任意）
# user_id: 不透明 ID（UUID 等）のみ。PII 禁止
```

### ログレベル基準

| レベル    | 用途                   | 例                                        |
| --------- | ---------------------- | ----------------------------------------- |
| `error`   | 即時対応が必要な異常   | DB 接続失敗・バッチ全件失敗・認証障害     |
| `warning` | 異常だが処理が継続可能 | バッチ一部失敗・リトライ発生・期限超過    |
| `info`    | 正常な業務イベント     | バッチ開始/完了・API リクエスト・ログイン |

### コード例

```python
import structlog

logger = structlog.get_logger()

# OK: 構造化ログ（request_id + 操作結果）
logger.info(
    "タスク作成",
    request_id=request_id,
    action="task.create",
    task_id=str(result.value.id),
)

# OK: エラーログ（PII なし・request_id あり）
logger.error(
    "タスク作成に失敗",
    request_id=request_id,
    action="task.create",
    error_type=error.type,
)

# NG: PII
logger.info(f"User {user.email} created task {task.title}")
```

---

## structlog 設定

```python
# app/logging_config.py
import structlog


def configure_logging() -> None:
    """構造化ログを設定する。"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

---

## ヘルスチェック

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session

router = APIRouter()


@router.get("/health")
def health_check(
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """ヘルスチェック（認証不要）。"""
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}
```

- `/health` は認証不要。DB 接続状態を含める。詳細情報は返さない。

---

## アラート発報

以下の条件でアラートを発報する設定とすること。

| 条件                           | 重大度   | 対処                               |
| ------------------------------ | -------- | ---------------------------------- |
| バッチ `FAILURE`（全件失敗）   | Critical | 即座にチームに通知・手動確認       |
| バッチ `PARTIAL_FAILURE`       | Warning  | ログを確認し、失敗レコードを再処理 |
| API の 5xx 連続発生（3 件/分） | Critical | インフラ・DB 接続を確認            |
| ヘルスチェック失敗             | Critical | サーバー・DB の状態を確認          |
| 期限超過タスクの大量発生       | Warning  | 業務担当者に通知                   |

> ASSUMPTION: アラート通知の具体的な宛先（メール・Slack・Teams 等）はインフラ設定で確定する。
> ここではアプリケーション層のログ出力条件のみを定義する。

---

## バッチ監視

`BatchResult` をログ出力し監視ツールで検索。

```python
import structlog

from app.batch.types import BatchResult

logger = structlog.get_logger()


def log_batch_result(result: BatchResult) -> None:
    """バッチ結果をログ出力する。"""
    duration_ms = int(
        (result.finished_at - result.started_at).total_seconds() * 1000
    )
    log_data = {
        "batch_name": result.batch_name,
        "status": result.status,
        "processed_count": result.processed_count,
        "failed_count": result.failed_count,
        "skipped_count": result.skipped_count,
        "duration_ms": duration_ms,
    }

    if result.status == "SUCCESS":
        logger.info("バッチ完了", **log_data)
    elif result.status == "PARTIAL_FAILURE":
        logger.warning("バッチ一部失敗", **log_data)
    else:
        logger.error("バッチ失敗", **log_data)
```

---

## API リクエストログ

すべての API リクエストに対してアクセスログを出力する。

```python
# app/middleware/logging.py
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "アクセスログ",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=getattr(request.state, "user_id", None),
        )
        return response
```

記録してはならない値:

- リクエストボディ（PII が含まれる可能性）
- Authorization ヘッダーの値
- クエリパラメータの値（PII が含まれる可能性がある場合）
