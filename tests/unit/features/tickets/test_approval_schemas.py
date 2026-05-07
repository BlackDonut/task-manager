"""承認フロー Pydantic スキーマのユニットテスト。

テスト対象: app/features/tickets/approval/schemas.py
テスト方針: バリデーション境界値・型制約を純粋関数として検証（DB・モック不要）
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.features.tickets.approval.schemas import (
    CreateApprovalRequest,
    ReviewApprovalRequest,
)


class TestCreateApprovalRequest:
    """CreateApprovalRequest のスキーマバリデーションテスト。"""

    def test_正常なタイトルで生成できる(self) -> None:
        # Arrange / Act
        req = CreateApprovalRequest(title="リリース承認申請")

        # Assert
        assert req.title == "リリース承認申請"

    def test_タイトルが空文字列の場合バリデーションエラーになる(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValidationError) as exc_info:
            CreateApprovalRequest(title="")

        assert "title" in str(exc_info.value)

    def test_タイトルが200文字の場合は正常に生成できる(self) -> None:
        # Arrange
        title = "a" * 200

        # Act
        req = CreateApprovalRequest(title=title)

        # Assert
        assert len(req.title) == 200

    def test_タイトルが201文字の場合バリデーションエラーになる(self) -> None:
        # Arrange
        title = "a" * 201

        # Act / Assert
        with pytest.raises(ValidationError) as exc_info:
            CreateApprovalRequest(title=title)

        assert "title" in str(exc_info.value)

    def test_タイトルが必須フィールドである(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            CreateApprovalRequest()  # type: ignore[call-arg]


class TestReviewApprovalRequest:
    """ReviewApprovalRequest のスキーマバリデーションテスト。"""

    def test_approve_アクションで生成できる(self) -> None:
        # Arrange / Act
        req = ReviewApprovalRequest(action="approve")

        # Assert
        assert req.action == "approve"
        assert req.comment is None

    def test_reject_アクションでコメント付きで生成できる(self) -> None:
        # Arrange / Act
        req = ReviewApprovalRequest(action="reject", comment="要件不足のため却下")

        # Assert
        assert req.action == "reject"
        assert req.comment == "要件不足のため却下"

    def test_不正なactionの場合バリデーションエラーになる(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValidationError) as exc_info:
            ReviewApprovalRequest(action="unknown")  # type: ignore[arg-type]

        assert "action" in str(exc_info.value)

    def test_コメントが2000文字の場合は正常に生成できる(self) -> None:
        # Arrange
        comment = "a" * 2000

        # Act
        req = ReviewApprovalRequest(action="approve", comment=comment)

        # Assert
        assert len(req.comment) == 2000  # type: ignore[arg-type]

    def test_コメントが2001文字の場合バリデーションエラーになる(self) -> None:
        # Arrange
        comment = "a" * 2001

        # Act / Assert
        with pytest.raises(ValidationError) as exc_info:
            ReviewApprovalRequest(action="approve", comment=comment)

        assert "comment" in str(exc_info.value)

    def test_actionが必須フィールドである(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            ReviewApprovalRequest()  # type: ignore[call-arg]
