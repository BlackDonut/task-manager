"""state_machine.validate_transition のユニットテスト。

仕様ソース: app/common/state_machine.py
"""

from __future__ import annotations

import pytest

from app.common.state_machine import validate_transition

# テスト用遷移マップ
_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"approved", "rejected"}),
    "approved": frozenset(),
    "rejected": frozenset(),
}


class TestValidateTransition:
    """validate_transition の正常系・異常系テスト。"""

    def test_pending_to_approved_は許可される(self) -> None:
        # Arrange / Act
        result = validate_transition("pending", "approved", _TRANSITIONS)

        # Assert
        assert result is True

    def test_pending_to_rejected_は許可される(self) -> None:
        # Arrange / Act
        result = validate_transition("pending", "rejected", _TRANSITIONS)

        # Assert
        assert result is True

    def test_approved_はすべての遷移を拒否する(self) -> None:
        # Arrange / Act
        result = validate_transition("approved", "pending", _TRANSITIONS)

        # Assert
        assert result is False

    def test_rejected_はすべての遷移を拒否する(self) -> None:
        # Arrange / Act
        result = validate_transition("rejected", "approved", _TRANSITIONS)

        # Assert
        assert result is False

    def test_存在しないステータスからの遷移は拒否される(self) -> None:
        # Arrange / Act
        result = validate_transition("unknown", "approved", _TRANSITIONS)

        # Assert
        assert result is False

    def test_同一ステータスへの遷移が遷移マップ外の場合は拒否される(self) -> None:
        # Arrange / Act
        result = validate_transition("pending", "pending", _TRANSITIONS)

        # Assert
        assert result is False
