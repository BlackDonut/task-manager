"""SQLAlchemy 非同期エンジン + FastAPI セッション依存性注入。

接続文字列は環境変数 DB_URL で設定する（.env ファイルまたは環境変数）。

Windows 認証の例:
  DB_URL=mssql+aioodbc://./task_manager_db?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes

SQL Server 認証の例:
  DB_URL=mssql+aioodbc://SA:password@localhost/task_manager_db?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes

前提:
  - ODBC Driver 17 or 18 for SQL Server がホストにインストールされていること
  - pip install -e ".[dev]" で sqlalchemy[asyncio] および aioodbc がインストール済みであること
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# --- エンジン・セッションファクトリ（起動時 1 回のみ生成） -----------------

def _build_engine():  # type: ignore[return]
    settings = get_settings()
    # .env は pyodbc スキームで記載する運用に統一する。
    # SQLAlchemy 非同期エンジンには aioodbc が必要なので、ここで変換する。
    async_url = settings.database_url.replace("mssql+pyodbc", "mssql+aioodbc", 1)
    return create_async_engine(
        async_url,
        pool_pre_ping=True,  # 切断検知
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is None:
        _engine = _build_engine()
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


# --- FastAPI Depends 用依存性 -----------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends で使用する DB セッション依存性。

    使用例:
        async def endpoint(session: AsyncSession = Depends(get_db)) -> ...:
    """
    factory = _get_session_factory()
    async with factory() as session:
        yield session
