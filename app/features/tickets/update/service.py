"""チケット更新 Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.update.repository import TicketUpdateRepository
from app.features.tickets.update.schemas import TicketUpdateRequest, TicketUpdateResponse


class TicketUpdateService:
    """チケット更新ユースケース。"""

    def __init__(self, repository: TicketUpdateRepository) -> None:
        self._repository = repository

    async def update(
        self,
        ticket_id: int,
        req: TicketUpdateRequest,
        scope: OrganizationScope,
    ) -> Result[TicketUpdateResponse]:
        """チケットを更新する。

        Args:
            ticket_id: 更新対象チケット ID
            req: チケット更新リクエスト
            scope: 認証済みユーザーの組織スコープ

        Returns:
            Ok(TicketUpdateResponse): 更新済みチケット
            Err(AppError): 検証エラー / DB エラー時
        """
        return await self._repository.update(ticket_id, req, scope)
