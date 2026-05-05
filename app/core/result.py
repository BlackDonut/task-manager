"""Result 型定義（Ok / Err / AppError）。

仕様ソース: ``.github/instructions/python.instructions.md`` §Result パターン

Service / Repository の全メソッドは ``Result[T]`` を返す（L2 ルール）。
Service 層から外部に ``raise`` で例外伝播することを禁止する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeGuard, TypeVar

try:
    # Python 3.13+ では typing に TypeIs が入る
    from typing import TypeIs  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import TypeIs

T = TypeVar("T")

# 業務エラー分類。HTTP ステータスへのマッピングは ``app/common/result_to_http.py`` 参照
ErrorType = Literal[
    "NOT_FOUND",
    "VALIDATION",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "CONFLICT",
    "BUSINESS_RULE",
    "INTERNAL",
]


@dataclass(frozen=True, slots=True)
class AppError:
    """業務エラー情報。

    ``details`` はログ用の内部情報。レスポンスには含めない（情報漏洩防止 L1）。
    """

    type: ErrorType
    message: str
    details: object | None = None


@dataclass(frozen=True, slots=True)
class Ok[T]:
    """成功結果。``value`` に正常系の値を保持する。"""

    value: T
    ok: Literal[True] = True


@dataclass(frozen=True, slots=True)
class Err:
    """失敗結果。``error`` に ``AppError`` を保持する。"""

    error: AppError
    ok: Literal[False] = False


# Result 型: 成功 or 失敗の直和
type Result[T] = Ok[T] | Err


def is_ok[T](result: Result[T]) -> TypeIs[Ok[T]]:
    """``result`` が Ok かを判定する型ガード（TypeIs で両分岐をナロー）。"""
    return result.ok is True


def is_err[T](result: Result[T]) -> TypeGuard[Err]:
    """``result`` が Err かを判定する型ガード。"""
    return result.ok is False
