"""リスクダッシュボード Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.risk.repository import RiskDashboardRepository
from app.features.tickets.risk.schemas import RiskDashboardQuery, RiskDashboardResponse


class RiskDashboardService:
    """リスクダッシュボード取得のユースケース。"""

    def __init__(self, repository: RiskDashboardRepository) -> None:
        self._repository = repository

    async def get_risk_dashboard(
        self,
        query: RiskDashboardQuery,
        scope: OrganizationScope,
    ) -> Result[RiskDashboardResponse]:
        """遅延・リスクチケットの集計とリストを取得する。

        Args:
            query: フィルタパラメータ
            scope: 認証済みユーザーの組織スコープ（データ境界チェックに使用）
        """
        return await self._repository.get_risk_dashboard(query, scope)
