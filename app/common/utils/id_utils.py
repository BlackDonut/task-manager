"""ID 生成ユーティリティ。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.6

- UUID v4 を標準とし、運用で UUID v7 に切り替える際は本モジュールのみ修正する
- PII を含まない不透明 ID として、ログ・セッション・一括操作 ID に利用する
"""

from __future__ import annotations

import uuid


def generate_uuid() -> str:
    """UUID v4 文字列生成。"""
    return str(uuid.uuid4())


def generate_operation_id() -> str:
    """一括操作 ID 生成。

    AuditLog と BulkOperation の紐付けキーとして利用する（bulk-operation.instructions.md）。
    """
    return generate_uuid()


def generate_request_id() -> str:
    """リクエスト ID 生成（分散トレース用）。"""
    return generate_uuid()


def is_valid_uuid(value: str) -> bool:
    """UUID 形式バリデーション（v1〜v5 を許容）。"""
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True
