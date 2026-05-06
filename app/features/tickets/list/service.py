"""チケット一覧 Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.list.repository import TicketListRepository
from app.features.tickets.list.schemas import TicketListQuery, TicketListResponse


class TicketListService:
    """チケット一覧の取得ユースケース。"""

    def __init__(self, repository: TicketListRepository) -> None:
        self._repository = repository

    async def get_list(
        self,
        query: TicketListQuery,
        scope: OrganizationScope,
    ) -> Result[TicketListResponse]:
        """チケット一覧を取得する。

        Args:
            query: フィルタ・ページネーションパラメータ
            scope: 認証済みユーザーの組織スコープ（データ境界チェックに使用）
        """
        return await self._repository.get_list(query, scope)
