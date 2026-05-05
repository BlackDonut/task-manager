"""業務共通バリデーション関数・エラーファクトリ。

仕様ソース: ``docs/03_detail-design/01_common/common-functions.md``
業務制約: 業務上絶対条件 #3（人間は必ずミスをする前提で設計）の機械的担保。

--- 初学者向けガイド ---
このファイルには 2 種類の関数があります。

【バリデーション関数】: True/False や Ok/Err を返す検証ロジック
  例: validate_four_eyes_principle()  承認者 ≠ 申請者をチェック

【エラーファクトリ】: よく使う Err オブジェクトを生成するヘルパー
  例: not_found_err("Task")  → Err(AppError(type="NOT_FOUND", ...)) を返す

各 Service では以下のように使います:
  row = self._repo.find_by_id(id, scope)
  if row is None:
      return not_found_err("Task")   # ← これでエラーレスポンスを返せる
"""

from __future__ import annotations

from app.core.result import AppError, Err, Ok, Result


def validate_four_eyes_principle(
    requester_id: str,
    approver_id: str,
) -> Result[None]:
    """四眼原則（起票者 ≠ 承認者）を検証する。

    業務上絶対条件 #3 の担保。承認系オペレーション全般で再利用する。
    タスク承認・期日変更承認・フェーズ移行承認 等、二重チェックを要するすべての
    決裁系メソッドの冒頭で呼び出すこと。

    Args:
        requester_id: 起票者のユーザー ID。
        approver_id: 承認者のユーザー ID。

    Returns:
        起票者と承認者が同一の場合 ``Err(BUSINESS_RULE)``、そうでなければ ``Ok(None)``。
    """
    if requester_id == approver_id:
        return Err(
            error=AppError(
                type="BUSINESS_RULE",
                message="Four-eyes principle: requester and approver must be different users",
            )
        )
    return Ok(value=None)


# ── エラーファクトリ（共通パターンの簡略化） ───────────────────────────────
#
# 以下の関数は各 Service で繰り返し使われる Err 生成を共通化したものです。
# 20+ 箇所で同じコードが繰り返されていたため、2 回目ルール
# (deduplication.instructions.md §2) に基づき抽出しました。
#
# 使い方:
#   from app.common.validators import not_found_err, internal_err
#   ...
#   if row is None:
#       return not_found_err("Task")   # "Task not found" エラーを返す


def not_found_err(entity: str) -> Err:
    """エンティティが存在しない場合の NOT_FOUND エラーを生成する。

    Service の find 系メソッドで ``row is None`` のときに使う。
    HTTP レスポンスは ``result_to_http.py`` が 404 に変換する。

    Args:
        entity: エンティティ名（例: "Task", "Application"）。
                エラーメッセージに ``"{entity} not found"`` として埋め込まれる。

    Returns:
        ``AppError(type="NOT_FOUND", message="{entity} not found")`` をラップした ``Err``。

    使用例::

        row = self._repo.find_by_id(task_id, scope)
        if row is None:
            return not_found_err("Task")
    """
    return Err(error=AppError(type="NOT_FOUND", message=f"{entity} not found"))


def internal_err(message: str, details: object | None = None) -> Err:
    """予期しない内部エラーを生成する。

    ``except`` ブロックで発生した例外を Service 外に伝播させずに
    ``Result`` として返すための共通ファクトリ。
    HTTP レスポンスは ``result_to_http.py`` が 500 に変換する。

    セキュリティ（L1）: ``message`` に例外のスタックトレースや内部情報を
    含めないこと。``details`` はログ用で、レスポンスには含まれない。

    Args:
        message: クライアント向けメッセージ（"Failed to fetch tasks" 等）。
        details: ログ用内部詳細（例外メッセージ等）。省略可。

    Returns:
        ``AppError(type="INTERNAL", ...)`` をラップした ``Err``。

    使用例::

        try:
            rows = self._repo.list_all(scope)
        except Exception as exc:
            self._log.error("tasks.list_all.failed", error=str(exc))
            return internal_err("Failed to fetch tasks", details=str(exc))
    """
    return Err(error=AppError(type="INTERNAL", message=message, details=details))
