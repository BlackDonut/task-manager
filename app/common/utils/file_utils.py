"""ファイル I/O ユーティリティ。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.3

- 副作用ありのため戻り値は ``Result[T]`` でラップする（L2）
- パストラバーサル防止は ``path_utils.safe_join`` と併用する
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.result import AppError, Err, Ok, Result

# アップロード許可拡張子（L1: 実行可能ファイル禁止）
ALLOWED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".xlsx",
        ".xls",
        ".csv",
        ".docx",
        ".doc",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".txt",
        ".zip",
    }
)

# 最大ファイルサイズ（MB）。運用上の制限値
MAX_UPLOAD_SIZE_MB: float = 50.0

# ハッシュ計算時のチャンクサイズ（大容量ファイルのメモリ爆発対策）
_HASH_CHUNK_SIZE: int = 8192


def read_text_file(path: Path) -> Result[str]:
    """テキストファイル読み込み（UTF-8）。"""
    if not path.is_file():
        return Err(error=AppError(type="NOT_FOUND", message=f"File not found: {path.name}"))
    try:
        return Ok(value=path.read_text(encoding="utf-8"))
    except OSError as e:
        return Err(error=AppError(type="INTERNAL", message="File read error", details=str(e)))


def write_text_file(path: Path, content: str) -> Result[None]:
    """テキストファイル書き込み（UTF-8）。親ディレクトリ自動作成。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as e:
        return Err(error=AppError(type="INTERNAL", message="File write error", details=str(e)))
    return Ok(value=None)


def get_file_size_mb(path: Path) -> float:
    """ファイルサイズを MB で返す。"""
    return path.stat().st_size / (1024 * 1024)


def validate_file_extension(filename: str, allowed: set[str] | None = None) -> bool:
    """拡張子バリデーション。allowed 省略時は ``ALLOWED_UPLOAD_EXTENSIONS``。"""
    ext = Path(filename).suffix.lower()
    target = allowed if allowed is not None else ALLOWED_UPLOAD_EXTENSIONS
    return ext in target


def compute_file_hash(path: Path, algorithm: str = "sha256") -> Result[str]:
    """ファイルハッシュ計算（チャンク読み込み）。"""
    if not path.is_file():
        return Err(error=AppError(type="NOT_FOUND", message=f"File not found: {path.name}"))
    try:
        h = hashlib.new(algorithm)
        with path.open("rb") as f:
            for block in iter(lambda: f.read(_HASH_CHUNK_SIZE), b""):
                h.update(block)
    except (OSError, ValueError) as e:
        return Err(error=AppError(type="INTERNAL", message="Hash computation error", details=str(e)))
    return Ok(value=h.hexdigest())


def ensure_directory(path: Path) -> Result[None]:
    """ディレクトリ存在確認 & 作成。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return Err(error=AppError(type="INTERNAL", message="Directory creation error", details=str(e)))
    return Ok(value=None)
