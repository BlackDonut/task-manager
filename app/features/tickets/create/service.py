"""チケット作成 Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.create.repository import TicketCreateRepository
from app.features.tickets.create.schemas import TicketCreateRequest, TicketCreateResponse


class TicketCreateService:
    """チケット作成ユースケース。"""

    def __init__(self, repository: TicketCreateRepository) -> None:
        self._repository = repository

    async def create(
        self,
        req: TicketCreateRequest,
        scope: OrganizationScope,
    ) -> Result[TicketCreateResponse]:
        """チケットを新規作成する。

        Args:
            req: チケット作成リクエスト
            scope: 認証済みユーザーの組織スコープ

        Returns:
            Ok(TicketCreateResponse): 作成済みチケット
            Err(AppError): 検証エラー / DB エラー時
        """
        return await self._repository.create(req, scope)
