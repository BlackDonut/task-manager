"""セッション関連の定数。

セッションミドルウェア本体と分離して配置することで、WebSocket Router や
IIS 認証ミドルウェアが中身の依存（redis, structlog 等）を引き込まずに
Cookie 名・Redis キー接頭辞だけを参照できるようにする。

仕様ソース: ``docs/02_basic-design/01_common/basic-design.md`` §認証フロー
"""

from __future__ import annotations

COOKIE_NAME = "task-manager.sid"
REDIS_KEY_PREFIX = "task-mgr:sess:"
SESSION_ID_BYTES = 32  # secrets.token_urlsafe(32) → 256-bit entropy
