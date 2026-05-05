"""文字列操作ユーティリティ。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.1

- ``mask_pii`` は PII を含むデバッグ表示の最終防衛線。本番ログには元々 PII を
  載せないこと（L1）。PII マスキング関数があることは PII 記録を許可しない
"""

from __future__ import annotations

import re
import unicodedata

# ファイル名に使えない文字（Windows/Linux 両対応）
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# PascalCase/camelCase → snake_case 変換用
_CAMEL_BOUNDARY_1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY_2 = re.compile(r"([a-z\d])([A-Z])")


def truncate(value: str, max_length: int, suffix: str = "…") -> str:
    """最大長で切り詰め。suffix を末尾に付与する。"""
    if max_length <= 0:
        raise ValueError("max_length must be > 0")
    if len(value) <= max_length:
        return value
    if max_length <= len(suffix):
        return suffix[:max_length]
    return value[: max_length - len(suffix)] + suffix


def normalize_whitespace(value: str) -> str:
    """連続空白を 1 つに正規化し前後空白を除去する。"""
    return re.sub(r"\s+", " ", value).strip()


def to_snake_case(value: str) -> str:
    """PascalCase / camelCase → snake_case。"""
    s = _CAMEL_BOUNDARY_1.sub(r"\1_\2", value)
    s = _CAMEL_BOUNDARY_2.sub(r"\1_\2", s)
    return s.lower().replace("-", "_")


def to_camel_case(value: str) -> str:
    """snake_case → camelCase。"""
    parts = value.split("_")
    if not parts:
        return value
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def mask_pii(value: str, visible_chars: int = 2) -> str:
    """PII マスキング。先頭 N 文字以外を * に置換する。"""
    if visible_chars < 0:
        raise ValueError("visible_chars must be >= 0")
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)


def is_blank(value: str | None) -> bool:
    """None・空文字・空白のみを True 判定する。"""
    return value is None or value.strip() == ""


def safe_strip(value: str | None) -> str:
    """None 安全な strip()。None → 空文字。"""
    return "" if value is None else value.strip()


def sanitize_filename(filename: str) -> str:
    """ファイル名に使用不可な文字を除去する（パストラバーサル防止）。"""
    # パス区切りを除去（..  をそのまま残しても拡張子判定で無効化される構造を維持）
    name = filename.replace("/", "").replace("\\", "")
    name = _UNSAFE_FILENAME_CHARS.sub("", name)
    # Unicode 正規化（全角/半角の差による衝突を抑制）
    name = unicodedata.normalize("NFC", name)
    # 先頭のドットを除去（隠しファイル・相対パス表記の防止）
    name = name.lstrip(".")
    return name or "unnamed"


def generate_display_id(prefix: str, sequence: int, width: int = 4) -> str:
    """表示用 ID 生成。例: ``("T", 21)`` → ``"T-0021"``。"""
    if sequence < 0:
        raise ValueError("sequence must be >= 0")
    if width < 1:
        raise ValueError("width must be >= 1")
    return f"{prefix}-{sequence:0{width}d}"
