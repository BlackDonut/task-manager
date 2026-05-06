"""環境変数・設定管理（pydantic-settings）。

仕様ソース:
- ``docs/guides/environment-variables.md``
- ``docs/03_detail-design/01_common/common-backend.md``

全ての環境依存値は本モジュール経由で取得する。モジュール内で ``os.getenv``
を直接呼ぶことを禁止する（L2 警告）。

セキュリティ:
- シークレットはコードに書かない（L1）。常に環境変数経由
- ``Settings.model_dump()`` をログに出力する場合は ``secret_redis_password`` 等の
  機密フィールドを事前に除外すること
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[explicit-any]
    """アプリケーション設定。

    ``.env`` ファイル + 環境変数から読み込む。環境変数が優先される。
    """

    # --- アプリケーション ---
    app_name: str = "task-manager"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False

    # --- Redis（セッション） ---
    redis_url: str = "redis://localhost:6379/0"
    redis_password: SecretStr | None = None

    # --- セッション ---
    session_cookie_secure: bool = False  # production では True
    session_max_age_seconds: int = 28800  # 8 時間（auth-design.md §11.3）

    # --- LDAP（IIS Windows 認証フォールバック・アカウント有効性確認用） ---
    ldap_enabled: bool = False
    ldap_url: str = ""
    ldap_base_dn: str = ""
    ldap_bind_dn: str = ""
    ldap_bind_password: SecretStr | None = None
    ldap_user_search_filter: str = "(sAMAccountName={login_id})"

    # --- ファイルストレージ ---
    # 開発環境: ローカルフォルダ。本番: ファイルサーバの UNC パス or マウントポイントを設定する
    # ASSUMPTION: 本番では UNC パス（例: \\fileserver\task-manager\files）を環境変数で注入
    file_storage_root: str = Field(
        default="/srv/files",
        description="ファイルストレージルートパス。docs/guides/environment-variables.md 参照",
    )

    # --- データベース (SQL Server) ---
    # SA 認証例（.env の DATABASE_URL に設定する）:
    #   DATABASE_URL=mssql+pyodbc://sa:<password>@localhost:1433/<db>?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
    # Windows 認証例:
    #   DATABASE_URL=mssql+pyodbc://.//<db>?driver=ODBC+Driver+18+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes
    # ※ aioodbc への変換は app/core/database.py が行う
    database_url: str = Field(
        default="mssql+pyodbc://./task_manager_db?driver=ODBC+Driver+18+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes",
        description="SQLAlchemy 接続文字列（pyodbc スキーム）。非同期エンジン生成時に aioodbc へ変換される。",
    )

    # --- ロギング ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # --- Email（F-154: critical 通知のデリバリ） ---
    # ASSUMPTION: 本番では環境変数で注入。ローカル開発では smtp_enabled=False で無効化。
    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: SecretStr | None = None
    smtp_from_address: str = "noreply@task-manager.example.com"
    smtp_from_name: str = "タスク管理システム"
    # ユーザーのメールアドレスを {login_id}@{smtp_recipient_domain} で構築する。
    # PII を DB に持たない設計（L1）を前提に、Active Directory のドメインを設定する。
    smtp_recipient_domain: str = "example.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings のシングルトン取得。

    FastAPI の ``Depends`` で使用する。``lru_cache`` で複数回生成を防ぐ。
    テストでは ``get_settings.cache_clear()`` でクリアし、環境変数を差し替えて再取得する。
    """
    return Settings()
