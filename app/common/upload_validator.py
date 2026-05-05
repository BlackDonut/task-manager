"""Upload validator - shared MIME/size validation for file uploads."""

from __future__ import annotations

from fastapi import UploadFile

from app.core.result import AppError, Err, Ok, Result

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# アップロード制限定数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ファイルアップロードの最大サイズ（20 MB）
# ASSUMPTION: 20MB は certificates 機能で運用実績があり、これを基準とする。
# NOTE: app/common/utils/file_utils.py の MAX_UPLOAD_SIZE_MB (50MB) は
#       拡張子チェック専用のファイル操作ユーティリティ用であり、
#       HTTP アップロードのサイズ制限とは別の用途で残す。
UPLOAD_MAX_BYTES: int = 20 * 1024 * 1024  # 20 MB

# デフォルトの許可 MIME タイプ（PDF + 主要画像）
# RFC 7231 準拠の MIME タイプ文字列を使用する
DEFAULT_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    }
)

# Word / Excel ファイル用の許可 MIME タイプ
OFFICE_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    }
)


async def validate_and_read_upload(
    upload: UploadFile,
    allowed_mime_types: frozenset[str] = DEFAULT_ALLOWED_MIME_TYPES,
    max_bytes: int = UPLOAD_MAX_BYTES,
) -> Result[bytes]:
    """FastAPI の UploadFile を MIME タイプ・サイズで検証してバイト列を返す。

    【初学者向け】
    この関数が解決する問題:
    - アップロードされたファイルの MIME タイプが許可リストにあるか確認する
    - ファイルサイズが上限を超えていないか確認する
    - 問題がなければファイルの内容（bytes）を返す

    なぜ拡張子ではなく MIME タイプを使うか:
    - 拡張子は簡単に偽装できる（.jpg と名前を付けた実行ファイルなど）
    - MIME タイプはファイルの実際の形式を示す（HTTP プロトコルで送られる）
    - ただし MIME タイプも改ざん可能なため、必要に応じてマジックバイト検証を追加すること

    Args:
        upload:             FastAPI の UploadFile オブジェクト（Router で受け取るもの）。
        allowed_mime_types: 許可する MIME タイプのセット。デフォルトは PDF + 主要画像。
        max_bytes:          最大ファイルサイズ（バイト単位）。デフォルトは 20 MB。

    Returns:
        Ok(bytes)        検証通過: ファイルの生バイト列
        Err(VALIDATION)  MIME タイプ不許可 or サイズ超過

    Example::

        # Router での使い方
        async def upload_cert(file: UploadFile = File(...)):
            result = await validate_and_read_upload(file, DEFAULT_ALLOWED_MIME_TYPES)
            if is_err(result):
                raise_http_exception(result.error, request_id)
            file_bytes = result.value
    """
    # MIME タイプのチェック（content_type は HTTP リクエストのヘッダーから取得）
    content_type = upload.content_type or ""
    if content_type not in allowed_mime_types:
        allowed_list = ", ".join(sorted(allowed_mime_types))
        return Err(
            error=AppError(
                type="VALIDATION",
                message=f"File type '{content_type}' is not allowed. Allowed types: {allowed_list}",
            )
        )

    # ファイルを読み込む（await が必要: FastAPI の UploadFile は非同期）
    content = await upload.read()

    # サイズチェック（読み込んだ後に確認）
    if len(content) > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        actual_mb = len(content) / (1024 * 1024)
        return Err(
            error=AppError(
                type="VALIDATION",
                message=f"File size {actual_mb:.1f} MB exceeds the limit of {max_mb:.0f} MB",
            )
        )

    return Ok(value=content)
