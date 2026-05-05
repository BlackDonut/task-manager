"""RBAC 用の Action / Resource 定数。

仕様ソース: ``docs/03_detail-design/01_common/common-functions.md`` §2.5

認可チェックで文字列直書きは禁止。必ず本モジュールの StrEnum を参照する。

# TODO(domain): RBAC/ABAC 設計 ADR 承認後に粒度を確定する
"""

from __future__ import annotations

from enum import StrEnum


class Actions(StrEnum):
    """操作種別。"""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REQUEST = "request"
    SUBMIT = "submit"
    TRIAGE = "triage"
    MANAGE = "manage"
    PUBLISH = "publish"


class Resources(StrEnum):
    """保護対象リソース種別。"""

    TASK = "Task"
    APPLICATION = "Application"
    PRODUCT = "Product"
    PROJECT = "Project"
    COUNTRY = "Country"
    USER = "User"
    ORGANIZATION = "Organization"
    AUDIT_LOG = "AuditLog"
    SUBMISSION_COMPANY = "SubmissionCompany"
    APPLICATION_DOCUMENT = "ApplicationDocument"
    CERTIFICATE = "Certificate"
    PRODUCT_COUNTRY = "ProductCountry"
    SHIPPING_GATE = "ShippingGate"
    TASK_DEPENDENCY = "TaskDependency"
    TASK_COMMENT = "TaskComment"
    TASK_BACKLOG = "TaskBacklog"
    TASK_TEMPLATE = "TaskTemplate"
    WATCHER = "Watcher"
    APPLICATION_DEPENDENCY = "ApplicationDependency"
    NOTIFICATION = "Notification"
    NOTIFICATION_PREFERENCE = "NotificationPreference"
    ESCALATION_RULE = "EscalationRule"
    DATE_CHANGE_REQUEST = "DateChangeRequest"
    DELEGATION = "Delegation"
    ROLE = "Role"
    DEPARTMENT = "Department"
    PRODUCT_COMPONENT = "ProductComponent"
    SUBMISSION_BATCH = "SubmissionBatch"
    # 申請手順書（SCR004D §手順書タブ）。編集は procedure_edit 権限ロールのみ。
    APPLICATION_PROCEDURE = "ApplicationProcedure"
    TASK_MESSAGE = "TaskMessage"
    # 規制URL監視設定（SCR023）。SystemAdmin のみ CRUD 可。
    REG_WATCH_URL = "RegWatchUrl"
    # 再申請管理（SCR041）。再申請トリガー登録・ステータス遷移。
    REAPPLICATION = "ReApplication"
    # 書類テンプレートマスタ（SCR015）。マスタ管理者 / SystemAdmin のみ CRUD 可。
    DOCUMENT_TEMPLATE = "DocumentTemplate"
    # システムお知らせ（SCR036）。READ=全ユーザー / MANAGE=SystemAdmin のみ。
    SYSTEM_ANNOUNCEMENT = "SystemAnnouncement"
