"""DAG（有向非巡回グラフ）型定義。

仕様ソース:
- ``docs/03_detail-design/01_common/common-functions.md`` §2.6
- ``.github/instructions/dag-calculation.instructions.md``

タスク依存関係の期日連鎖計算（CPM: クリティカルパス法）で共通利用する。
循環検出と計算ロジックは Phase 4 の ``app/features/tasks/`` 配下で実装する。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DagNode(BaseModel):  # type: ignore[explicit-any]
    """DAG のノード（1 タスクに対応）。日時は ISO 8601 UTC 文字列。"""

    id: str
    earliest_start: str
    earliest_finish: str
    latest_start: str
    latest_finish: str
    total_float: int = Field(
        ...,
        description="余裕日数。0 ならクリティカルパス上",
        ge=0,
    )
    is_critical_path: bool


class DagEdge(BaseModel):  # type: ignore[explicit-any]
    """DAG の依存エッジ（先行 → 後続）。"""

    from_task_id: str
    to_task_id: str


class DagGraph(BaseModel):  # type: ignore[explicit-any]
    """ノード集合とエッジ集合の束。"""

    nodes: list[DagNode]
    edges: list[DagEdge]
