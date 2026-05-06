"""ガントチャート Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.gantt.repository import GanttTicketRepository
from app.features.tickets.gantt.schemas import GanttTicketListResponse, GanttTicketQuery


class GanttTicketService:
    """ガントチャート用チケット取得のユースケース。"""

    def __init__(self, repository: GanttTicketRepository) -> None:
        self._repository = repository

    async def get_gantt_list(
        self,
        query: GanttTicketQuery,
        scope: OrganizationScope,
    ) -> Result[GanttTicketListResponse]:
        """ガントチャート表示用チケット一覧を取得する。

        Args:
            query: フィルタパラメータ
            scope: 認証済みユーザーの組織スコープ（データ境界チェックに使用）
        """
        return await self._repository.get_gantt_list(query, scope)
