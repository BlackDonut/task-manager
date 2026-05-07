"""チケット添付ファイル API の Pydantic スキーマ定義。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---- レスポンス -----------------------------------------------------------


class AttachmentUploaderResponse(BaseModel):
    """添付ファイルアップロード者情報。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class AttachmentResponse(BaseModel):
    """添付ファイル 1 件のレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    original_filename: str = Field(description="元のファイル名（表示用）")
    file_size: int = Field(description="ファイルサイズ（バイト）")
    content_type: str = Field(description="MIME タイプ")
    uploader: AttachmentUploaderResponse
    created_at: str


class AttachmentListResponse(BaseModel):
    """添付ファイル一覧レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[AttachmentResponse]
    total: int
