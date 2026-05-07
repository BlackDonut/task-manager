"""フェーズ進捗マトリクス Service。

ビジネスロジック層。HTTP 知識を持たず、Result パターンで返す（L2 ルール）。
"""

from __future__ import annotations

from app.core.auth.models import OrganizationScope
from app.core.result import Result
from app.features.tickets.matrix.repository import PhaseMatrixRepository
from app.features.tickets.matrix.schemas import PhaseMatrixQuery, PhaseMatrixResponse


class PhaseMatrixService:
    """フェーズ進捗マトリクス取得のユースケース。"""

    def __init__(self, repository: PhaseMatrixRepository) -> None:
        self._repository = repository

    async def get_phase_matrix(
        self,
        query: PhaseMatrixQuery,
        scope: OrganizationScope,
    ) -> Result[PhaseMatrixResponse]:
        """製品×フェーズのマトリクスデータを取得する。

        Args:
            query: フィルタパラメータ
            scope: 認証済みユーザーの組織スコープ（データ境界チェックに使用）
        """
        return await self._repository.get_phase_matrix(query, scope)
