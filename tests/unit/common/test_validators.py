"""validate_four_eyes_principle のユニットテスト。

仕様ソース: app/common/validators.py
"""

from __future__ import annotations

from app.common.validators import validate_four_eyes_principle
from app.core.result import Err, Ok


class TestValidateFourEyesPrinciple:
    """四眼原則バリデーション: 申請者と承認者が異なることを検証。"""

    def test_申請者と承認者が異なる場合はOkを返す(self) -> None:
        # Arrange
        requester_id = "user-001"
        approver_id = "user-002"

        # Act
        result = validate_four_eyes_principle(requester_id, approver_id)

        # Assert
        assert isinstance(result, Ok)
        assert result.value is None

    def test_申請者と承認者が同一の場合はBUSINESS_RULEエラーを返す(self) -> None:
        # Arrange
        requester_id = "user-001"
        approver_id = "user-001"

        # Act
        result = validate_four_eyes_principle(requester_id, approver_id)

        # Assert
        assert isinstance(result, Err)
        assert result.error.type == "BUSINESS_RULE"

    def test_異なるUUID形式のIDでOkを返す(self) -> None:
        # Arrange
        requester_id = "00000000-0000-0000-0000-000000000001"
        approver_id = "00000000-0000-0000-0000-000000000002"

        # Act
        result = validate_four_eyes_principle(requester_id, approver_id)

        # Assert
        assert isinstance(result, Ok)
