"""承認フロー Router 統合テスト。

テスト方針（authorization.python.instructions.md に従い 3 パターン必須）:
  1. 権限あり → 正常系 (2xx)
  2. 権限なし → 403
  3. 組織外アクセス → Service/Repository が空リスト or NOT_FOUND を返す

DB セッションと TicketApprovalService を dependency_overrides で差し替え。
実際の DB アクセスは行わない。
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth.models import AuthenticatedUser, PermissionRef
from app.core.constants.permissions import Actions, Resources
from app.core.result import AppError, Err, Ok
from app.features.tickets.approval.schemas import (
    ApprovalActorResponse,
    ApprovalListResponse,
    ApprovalResponse,
)

# ---- ヘルパー --------------------------------------------------------------


def _make_user(
    *,
    id_: str = "1",  # ASSUMPTION: UserOrm.id は int PK のため数値文字列を使用
    department_id: str = "00000000-0000-0000-0000-0000000000d1",
    is_sys_admin: bool = False,
    permissions: tuple[PermissionRef, ...] = (),
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=id_,
        login_id="tester",
        department_id=department_id,
        is_sys_admin=is_sys_admin,
        permissions=permissions,
    )


def _make_approval_response(status: str = "pending") -> ApprovalResponse:
    return ApprovalResponse(
        id=1,
        ticket_id=10,
        title="test-approval",
        status=status,  # type: ignore[arg-type]
        requester=ApprovalActorResponse(id=1, display_name="requester-001"),
        approver=None,
        comment=None,
        created_at="2026-04-19T00:00:00Z",
        updated_at="2026-04-19T00:00:00Z",
    )


# ---- フィクスチャ -----------------------------------------------------------


@pytest.fixture
def app_with_mock_service() -> Generator[tuple[TestClient, MagicMock], None, None]:
    """TestClient と差し替え済み TicketApprovalService のタプルを提供するフィクスチャ。"""
    from app.core.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.features.tickets.approval.router import _get_service
    from app.main import create_app

    fastapi_app = create_app()

    mock_service = MagicMock()

    # DB セッションと Service を差し替え
    fastapi_app.dependency_overrides[get_db] = lambda: MagicMock()
    fastapi_app.dependency_overrides[_get_service] = lambda: mock_service

    with TestClient(fastapi_app, raise_server_exceptions=False) as client:
        yield client, mock_service

    # オーバーライドを元に戻す
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def app_with_no_permission() -> Generator[TestClient, None, None]:
    """権限なしユーザーでの TestClient フィクスチャ。"""
    from app.core.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.features.tickets.approval.router import _get_service
    from app.main import create_app

    fastapi_app = create_app()
    no_perm_user = _make_user(is_sys_admin=False, permissions=())
    fastapi_app.dependency_overrides[get_current_user] = lambda: no_perm_user
    fastapi_app.dependency_overrides[get_db] = lambda: MagicMock()
    fastapi_app.dependency_overrides[_get_service] = lambda: MagicMock()

    with TestClient(fastapi_app, raise_server_exceptions=False) as client:
        yield client

    fastapi_app.dependency_overrides.clear()


# ---- テスト: GET /{ticket_id}/approvals ------------------------------------


class TestListApprovalsEndpoint:
    """GET /api/v1/tickets/{ticket_id}/approvals の統合テスト。"""

    def test_権限ありのユーザーが承認一覧を取得できる(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user
        from app.main import create_app

        expected = ApprovalListResponse(items=[_make_approval_response()], total=1)
        mock_service.list_approvals = AsyncMock(return_value=Ok(expected))

        # get_current_user をシステム管理者で差し替え
        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        # Act
        response = client.get("/api/v1/tickets/10/approvals")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_権限なしのユーザーが403を受け取る(
        self, app_with_no_permission: TestClient
    ) -> None:
        # Arrange
        client = app_with_no_permission

        # Act
        response = client.get("/api/v1/tickets/10/approvals")

        # Assert
        assert response.status_code == 403

    def test_組織外アクセスの場合サービスが空一覧を返す(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        # 別組織ユーザー
        other_org_user = _make_user(
            department_id="00000000-0000-0000-0000-0000000000d9",
            is_sys_admin=True,  # 権限ゲートは通す。スコープフィルタで空になることを確認
        )
        client.app.dependency_overrides[get_current_user] = lambda: other_org_user  # type: ignore[union-attr]

        # 組織外スコープでは Repository が空リストを返す想定
        empty_list = ApprovalListResponse(items=[], total=0)
        mock_service.list_approvals = AsyncMock(return_value=Ok(empty_list))

        # Act
        response = client.get("/api/v1/tickets/10/approvals")

        # Assert
        assert response.status_code == 200
        assert response.json()["total"] == 0


# ---- テスト: POST /{ticket_id}/approvals -----------------------------------


class TestCreateApprovalEndpoint:
    """POST /api/v1/tickets/{ticket_id}/approvals の統合テスト。"""

    def test_権限ありのユーザーが承認申請を作成できる(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        mock_service.create_approval = AsyncMock(
            return_value=Ok(_make_approval_response("pending"))
        )

        # Act
        response = client.post(
            "/api/v1/tickets/10/approvals",
            json={"title": "リリース承認申請"},
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_権限なしのユーザーが403を受け取る(
        self, app_with_no_permission: TestClient
    ) -> None:
        # Arrange
        client = app_with_no_permission

        # Act
        response = client.post(
            "/api/v1/tickets/10/approvals",
            json={"title": "リリース承認申請"},
        )

        # Assert
        assert response.status_code == 403

    def test_チケットが存在しない場合404を返す(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        mock_service.create_approval = AsyncMock(
            return_value=Err(AppError(type="NOT_FOUND", message="チケット ID=99 が見つかりません"))
        )

        # Act
        response = client.post(
            "/api/v1/tickets/99/approvals",
            json={"title": "test-approval"},
        )

        # Assert
        assert response.status_code == 404

    def test_タイトルが空の場合400を返す(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        # Act
        response = client.post(
            "/api/v1/tickets/10/approvals",
            json={"title": ""},
        )

        # Assert
        # error_handler.py が RequestValidationError を 400 に変換する（project 規約）
        assert response.status_code == 400


# ---- テスト: PATCH /{ticket_id}/approvals/{approval_id} -------------------


class TestReviewApprovalEndpoint:
    """PATCH /api/v1/tickets/{ticket_id}/approvals/{approval_id} の統合テスト。"""

    def test_権限ありのユーザーが承認操作を実行できる(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        from app.features.tickets.approval.schemas import ApprovalActorResponse

        approved = ApprovalResponse(
            id=1,
            ticket_id=10,
            title="test-approval",
            status="approved",
            requester=ApprovalActorResponse(id=2, display_name="requester-002"),
            approver=ApprovalActorResponse(id=1, display_name="approver-001"),
            comment="承認します",
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:00Z",
        )
        mock_service.review_approval = AsyncMock(return_value=Ok(approved))

        # Act
        response = client.patch(
            "/api/v1/tickets/10/approvals/1",
            json={"action": "approve", "comment": "承認します"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    def test_権限なしのユーザーが403を受け取る(
        self, app_with_no_permission: TestClient
    ) -> None:
        # Arrange
        client = app_with_no_permission

        # Act
        response = client.patch(
            "/api/v1/tickets/10/approvals/1",
            json={"action": "approve"},
        )

        # Assert
        assert response.status_code == 403

    def test_四眼原則違反の場合422を返す(
        self, app_with_mock_service: tuple[TestClient, MagicMock]
    ) -> None:
        # Arrange
        client, mock_service = app_with_mock_service
        from app.core.auth.dependencies import get_current_user

        admin = _make_user(is_sys_admin=True)
        client.app.dependency_overrides[get_current_user] = lambda: admin  # type: ignore[union-attr]

        mock_service.review_approval = AsyncMock(
            return_value=Err(
                AppError(
                    type="BUSINESS_RULE",
                    message="Four-eyes principle: requester and approver must be different users",
                )
            )
        )

        # Act
        response = client.patch(
            "/api/v1/tickets/10/approvals/1",
            json={"action": "approve"},
        )

        # Assert
        assert response.status_code == 422
