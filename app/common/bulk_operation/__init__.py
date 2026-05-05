"""一括操作（TBL-011 BulkOperation）横断インフラ。

仕様ソース:
- ``docs/04_database/tables/TBL-011-bulk-operation.md``
- ``.github/instructions/bulk-operation.instructions.md``

BulkOperation は特定機能に紐づかない横断インフラのためここに配置する。
参照は ``from app.common.bulk_operation.models import BulkOperation`` のように
直接モジュールを指定すること（バレルエクスポートは行わない）。
"""
