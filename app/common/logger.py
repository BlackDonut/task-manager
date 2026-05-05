"""構造化ロガー（structlog）。

仕様ソース:
- ``docs/03_detail-design/01_common/common-backend.md`` §5.5
- ``.github/skills/monitoring/SKILL.md``

- ``print()`` 禁止。ログ出力は必ず本モジュール経由
- PII（氏名・メール等）をログに含めない（L1）。識別子は UUID のみ
- エラーは ``exc_info=True`` または ``log.exception(...)`` でトレースを残す

configure_logging() は ``app/main.py`` 起動時に 1 回だけ呼ぶ。
"""

from __future__ import annotations

import logging
import sys
from typing import cast

import structlog
from structlog.typing import Processor

from app.core.config import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    """structlog をアプリ全体で有効化する。

    JSON フォーマット（production）と console フォーマット（development）を切り替える。
    重複呼び出しは無害（structlog の configure は冪等）。
    """
    s = settings or get_settings()

    # 共通プロセッサ: メタ情報付与 → レンダラに渡すまでのパイプライン
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Processor
    if s.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[s.log_level],
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(**context: object) -> structlog.stdlib.BoundLogger:
    """リクエストスコープのロガーを取得する。

    使用例::

        log = get_logger(request_id=request_id, service="TasksService")
        log.info("task_updated", task_id=task_id)
        log.error("unexpected_error", exc_info=True)
    """
    # BoundLogger 型に narrow するために cast（structlog は型付けが弱いため）
    return cast("structlog.stdlib.BoundLogger", structlog.get_logger().bind(**context))
