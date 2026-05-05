"""Email 送信ユーティリティ（F-154: critical 通知のメール配信）。

仕様ソース:
- ``docs/01_requirements/feature-list.md`` F-154
- ``app/core/config.py`` smtp_* 設定

設計方針:
- SMTP 設定（``smtp_enabled=False``）の場合は送信をスキップしてログを出すのみ。
- PII 禁止（L1）: 本文・件名に氏名・メールアドレス等を含めない。
- recipient_email は呼び出し側が解決して渡す（本サービスは配信のみ担当）。
- 送信失敗は例外を raise しない。呼び出し側が Result パターンで受け取る。
"""

from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Final

from app.common.logger import get_logger
from app.core.config import Settings

_log = get_logger(service="email_sender")

# メール送信タイムアウト（秒）
_SMTP_TIMEOUT_SEC: Final[int] = 10


def send_email(
    *,
    settings: Settings,
    to_address: str,
    subject: str,
    body_text: str,
) -> bool:
    """テキスト形式のメールを 1 件送信する。

    Args:
        settings: アプリケーション設定（SMTP 接続情報）
        to_address: 送信先メールアドレス
        subject: 件名（PII を含めないこと）
        body_text: 本文テキスト（PII を含めないこと）

    Returns:
        True: 送信成功 / False: 無効化または失敗
    """
    if not settings.smtp_enabled:
        _log.info(
            "email_sender.skipped",
            reason="smtp_enabled=False",
            subject=subject,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to_address
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    password = settings.smtp_password.get_secret_value() if settings.smtp_password is not None else ""

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT_SEC) as server:
            if settings.smtp_use_tls:
                server.starttls(context=context)
            if settings.smtp_user:
                server.login(settings.smtp_user, password)
            server.sendmail(settings.smtp_from_address, to_address, msg.as_string())

        _log.info("email_sender.sent", subject=subject)
        return True

    except smtplib.SMTPAuthenticationError as exc:
        _log.error("email_sender.auth_failed", error=str(exc))
        return False
    except smtplib.SMTPRecipientsRefused as exc:
        _log.error("email_sender.recipient_refused", error=str(exc))
        return False
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        _log.error("email_sender.failed", error=str(exc))
        return False
