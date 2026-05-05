"""共通ユーティリティのバレルエクスポート。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md``

機能モジュール側は ``from app.common.utils import truncate, chunk`` のように
本モジュール経由でインポートする。個別ファイルから直接 import しない。
"""

from app.common.utils.collection_utils import (
    chunk,
    first_or_none,
    flatten,
    group_by,
    index_by,
    unique_by,
)
from app.common.utils.datetime_utils import (
    business_days_between,
    days_until,
    end_of_day,
    format_date,
    format_datetime,
    is_past,
    start_of_day,
    to_jst,
    to_utc,
)
from app.common.utils.excel_utils import (
    XLSX_MEDIA_TYPE,
    build_excel_bytes,
    excel_streaming_response,
    parse_excel_rows,
)
from app.common.utils.file_utils import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
    compute_file_hash,
    ensure_directory,
    get_file_size_mb,
    read_text_file,
    validate_file_extension,
    write_text_file,
)
from app.common.utils.id_utils import (
    generate_operation_id,
    generate_request_id,
    generate_uuid,
    is_valid_uuid,
)
from app.common.utils.path_utils import (
    get_extension,
    normalize_path,
    replace_extension,
    safe_join,
    unique_filename,
)
from app.common.utils.string_utils import (
    generate_display_id,
    is_blank,
    mask_pii,
    normalize_whitespace,
    safe_strip,
    sanitize_filename,
    to_camel_case,
    to_snake_case,
    truncate,
)
from app.common.utils.word_utils import (
    WordTableList,
    WordTableRow,
    parse_word_tables,
)

__all__ = [
    "ALLOWED_UPLOAD_EXTENSIONS",
    "MAX_UPLOAD_SIZE_MB",
    "business_days_between",
    "chunk",
    "compute_file_hash",
    "days_until",
    "end_of_day",
    "ensure_directory",
    "first_or_none",
    "flatten",
    "format_date",
    "format_datetime",
    "generate_display_id",
    "generate_operation_id",
    "generate_request_id",
    "generate_uuid",
    "get_extension",
    "get_file_size_mb",
    "group_by",
    "index_by",
    "is_blank",
    "is_past",
    "is_valid_uuid",
    "mask_pii",
    "normalize_path",
    "normalize_whitespace",
    "read_text_file",
    "replace_extension",
    "safe_join",
    "safe_strip",
    "sanitize_filename",
    "start_of_day",
    "to_camel_case",
    "to_jst",
    "to_snake_case",
    "to_utc",
    "truncate",
    "unique_by",
    "unique_filename",
    "validate_file_extension",
    "write_text_file",
    # Excel utilities
    "XLSX_MEDIA_TYPE",
    "build_excel_bytes",
    "excel_streaming_response",
    "parse_excel_rows",
    # Word utilities
    "WordTableList",
    "WordTableRow",
    "parse_word_tables",
]
