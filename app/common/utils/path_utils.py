"""パス操作ユーティリティ。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.4

セキュリティ: ``safe_join`` はパストラバーサル攻撃を防止する（L1）。
外部入力（アップロードファイル名等）を結合する場合は必ず本関数を経由すること。
"""

from __future__ import annotations

import posixpath
import uuid
from pathlib import Path

from app.core.result import AppError, Err, Ok, Result


def safe_join(base: Path, *parts: str) -> Result[Path]:
    """パストラバーサル防止付きのパス結合。

    結合後のパスが ``base`` 配下にない場合は VALIDATION エラーを返す。
    """
    resolved = (base / Path(*parts)).resolve()
    base_resolved = base.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        return Err(error=AppError(type="VALIDATION", message="Path traversal detected"))
    return Ok(value=resolved)


def get_extension(filename: str) -> str:
    """拡張子取得（小文字正規化）。"""
    return Path(filename).suffix.lower()


def replace_extension(filename: str, new_ext: str) -> str:
    """拡張子差し替え。``new_ext`` は '.' 付きで渡す。"""
    if not new_ext.startswith("."):
        raise ValueError("new_ext must start with '.'")
    return str(Path(filename).with_suffix(new_ext))


def unique_filename(filename: str, suffix: str | None = None) -> str:
    """ユニークファイル名生成。``suffix`` 省略時は UUID 短縮形を付与する。"""
    stem = Path(filename).stem
    ext = Path(filename).suffix
    tag = suffix or uuid.uuid4().hex[:8]
    return f"{stem}_{tag}{ext}"


def normalize_path(path: str) -> str:
    """パスの正規化（区切り文字を ``/`` に統一、``..`` を解決）。"""
    return posixpath.normpath(path.replace("\\", "/"))
