"""pytest 共通フィクスチャ。

仕様ソース: ``.github/instructions/common/testing.python.instructions.md``

- PII を含まないダミー値のみ利用する（L1）
- 時刻は ``FixedClock`` で固定し、現在日時に依存するテストを排除する（L2）
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    """各テストの前後で ``get_settings`` のキャッシュをクリアする。

    環境変数差し替えテストが他テストに漏れないようにする防御策。
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """テスト用 Settings。"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")  # テスト出力を静穏化
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def fixed_clock() -> FixedClock:
    """2026-04-19T00:00:00Z 固定の Clock。

    日時依存ロジックのテストで利用する。業務日付は全テストで同じ基準点から。
    """
    return FixedClock(datetime(2026, 4, 19, 0, 0, 0, tzinfo=UTC))


@pytest.fixture
def app_client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """FastAPI TestClient。

    ``test_settings`` を先に評価させることでテスト用設定を適用する。
    """
    # get_settings を test_settings 適用後に再評価させる
    _ = test_settings
    # アプリは import タイミングで create_app() を実行するため遅延 import
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def _strict_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト中に誤って本番 ``.env`` を読み込まないように ``APP_ENV=test`` を固定。"""
    monkeypatch.setenv("APP_ENV", "test")


# --- 認証・認可テスト用フィクスチャ ------------------------------------------
# 保護エンドポイントのテストでは以下 3 パターン必須（authorization.instructions.md）:
#   1. 権限あり（permission_required をパス）
#   2. 権限なし（403）
#   3. 組織外（Repository の OrganizationScope フィルタで空）


def make_authenticated_user(
    *,
    id_: str = "00000000-0000-0000-0000-000000000001",
    login_id: str = "tester",
    department_id: str = "00000000-0000-0000-0000-0000000000d1",
    is_sys_admin: bool = False,
    permissions: tuple[object, ...] = (),
) -> object:
    """テスト用 AuthenticatedUser ファクトリ。PII は含めない（L1）。"""
    from app.core.auth.models import AuthenticatedUser, PermissionRef

    typed_perms = tuple(p for p in permissions if isinstance(p, PermissionRef))
    return AuthenticatedUser(
        id=id_,
        login_id=login_id,
        department_id=department_id,
        is_sys_admin=is_sys_admin,
        permissions=typed_perms,
    )


@pytest.fixture
def sys_admin_user() -> object:
    """全権限バイパス用の SystemAdmin ユーザー。"""
    return make_authenticated_user(is_sys_admin=True)


@pytest.fixture
def no_permission_user() -> object:
    """権限を一切持たない一般ユーザー。"""
    return make_authenticated_user(is_sys_admin=False)
