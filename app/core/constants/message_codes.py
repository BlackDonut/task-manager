"""共通メッセージコード定数。

全エラーメッセージ・トースト通知で使うメッセージキーを一元管理する。
i18n リソースファイルのキーと同期を保つこと。

Router 層で ``I18n.t(MessageCodes.ERROR_NOT_FOUND, locale=locale)`` のように使う。
"""

from __future__ import annotations

from enum import StrEnum


class MessageCodes(StrEnum):
    """共通メッセージコード（i18n キー）。"""

    # --- エラー ---
    ERROR_NOT_FOUND = "error.not_found"
    ERROR_VALIDATION = "error.validation"
    ERROR_FORBIDDEN = "error.forbidden"
    ERROR_CONFLICT = "error.conflict"
    ERROR_BUSINESS_RULE = "error.business_rule"
    ERROR_INTERNAL = "error.internal"
    ERROR_UNAUTHORIZED = "error.unauthorized"
    ERROR_EXPORT_LIMIT_EXCEEDED = "error.export_limit_exceeded"

    # --- 成功 ---
    SUCCESS_CREATED = "success.created"
    SUCCESS_UPDATED = "success.updated"
    SUCCESS_DELETED = "success.deleted"
