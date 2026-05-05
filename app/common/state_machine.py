"""汎用ステータス遷移バリデーション。

仕様ソース: ``docs/03_detail-design/01_common/common-functions.md``

各機能の状態遷移マップはドメイン固有のため各 constants.py に残す。
検証ロジック（「from → to が許可されているか」の判定）のみを共通化する。

背景: deduplication.instructions.md §2 の 2 回目ルール。
6 ファイルで同一の「遷移マップ参照 → in 演算子」ロジックが重複していたため抽出。
  - applications/applications/constants.py: is_valid_necessity_transition()
  - applications/applications/state_machine.py: is_valid_application_transition()
  - applications/submission_batches/constants.py: can_transition()
  - applications/reapplication/constants.py: is_valid_reapplication_transition()
  - applications/document_templates/constants.py: is_valid_template_transition()
  - applications/shipping_gate/service.py: _can_transition()
"""

from __future__ import annotations

from typing import Any


def validate_transition(
    from_status: Any,
    to_status: Any,
    transitions: dict[Any, set[Any] | frozenset[Any]],
) -> bool:
    """状態遷移が許可されているかを検証する汎用関数。

    各機能の constants.py に定義された状態遷移マップを受け取り、
    from_status → to_status が許可されているかを判定する。

    文字列から Enum への変換などドメイン固有の前処理は呼び出し元で行うこと。

    Args:
        from_status: 遷移元ステータス（Enum または文字列）。
        to_status: 遷移先ステータス（Enum または文字列）。
        transitions: 状態遷移マップ（{from: set/frozenset[to]}）。

    Returns:
        遷移が許可されている場合 True、そうでなければ False。
        遷移マップに from_status が存在しない場合は False を返す。

    使用例::

        from app.common.state_machine import validate_transition

        def is_valid_necessity_transition(current: str, target: str) -> bool:
            try:
                from_status = NecessityStatus(current)
                to_status = NecessityStatus(target)
            except ValueError:
                return False
            return validate_transition(from_status, to_status, NECESSITY_STATUS_TRANSITIONS)
    """
    return to_status in transitions.get(from_status, frozenset())
