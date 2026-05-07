"""エスカレーションルール Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
業務制約:
  - delete_flg == 0 フィルタは省略禁止（論理削除 L1）
  - product_id は UNIQUE: 製品ごとに 1 ルールのみ
  - N+1 回避: product を joinedload で一括取得
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import Clock, SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.notifications.escalations.schemas import (
    BulkApplyResponse,
    EscalationRuleCreateRequest,
    EscalationRuleItem,
    EscalationRuleListResponse,
    EscalationRuleUpdateRequest,
)
from app.models.escalation_rule import EscalationRuleOrm
from app.models.product import ProductOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="escalations.repository")


def _to_item(rule: EscalationRuleOrm) -> EscalationRuleItem:
    """ORM → Pydantic 変換。"""
    return EscalationRuleItem(
        id=rule.id,
        product_id=rule.product_id,
        # product は joinedload で事前取得済みを前提とする
        product_name=rule.product.name,
        alert_days_before=rule.alert_days_before,
        escalation_days=rule.escalation_days,
        is_active=bool(rule.is_active),
    )


class EscalationRuleRepository:
    """エスカレーションルールのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or SystemClock()

    async def get_list(
        self,
        product_id: int | None,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時に使用
    ) -> Result[EscalationRuleListResponse]:
        """エスカレーションルール一覧を返す。

        Args:
            product_id: 絞り込む製品 ID。None の場合は全ルールを返す。
            scope: 組織スコープ（将来のマルチテナント対応時に使用）

        Returns:
            Ok(EscalationRuleListResponse)
            Err(AppError): DB アクセス失敗時
        """
        try:
            base_where = [EscalationRuleOrm.delete_flg == 0]
            if product_id is not None:
                base_where.append(EscalationRuleOrm.product_id == product_id)

            stmt = (
                select(EscalationRuleOrm)
                .options(joinedload(EscalationRuleOrm.product))
                .where(*base_where)
                .order_by(EscalationRuleOrm.id.asc())
            )
            rows = (await self._session.execute(stmt)).scalars().all()
            items = [_to_item(r) for r in rows]
        except Exception as exc:
            logger.error("escalations.list.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(EscalationRuleListResponse(items=items, total=len(items)))

    async def create(
        self,
        req: EscalationRuleCreateRequest,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[EscalationRuleItem]:
        """エスカレーションルールを新規作成する。

        Args:
            req: 作成リクエスト
            scope: 組織スコープ

        Returns:
            Ok(EscalationRuleItem): 作成されたルール
            Err(AppError): 製品が存在しない / 既にルールが存在する / DB エラー
        """
        try:
            # 製品の存在確認（論理削除済みも除外）
            product = (
                await self._session.execute(
                    select(ProductOrm).where(
                        ProductOrm.id == req.product_id,
                        ProductOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if product is None:
                return Err(AppError(type="NOT_FOUND", message="指定された製品が見つかりません"))

            # 重複チェック（同一製品に既存ルールがある場合は CONFLICT）
            existing = (
                await self._session.execute(
                    select(EscalationRuleOrm.id).where(
                        EscalationRuleOrm.product_id == req.product_id,
                        EscalationRuleOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return Err(
                    AppError(
                        type="CONFLICT",
                        message="この製品のエスカレーションルールは既に存在します",
                    )
                )

            now = self._clock.now().replace(tzinfo=None)  # DB は naive datetime で格納
            rule = EscalationRuleOrm(
                product_id=req.product_id,
                alert_days_before=req.alert_days_before,
                escalation_days=req.escalation_days,
                is_active=1 if req.is_active else 0,
                delete_flg=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(rule)
            await self._session.flush()  # id を確定させる

            # product を取得済みオブジェクトとして紐づける（joinedload 代替）
            rule.product = product
        except Exception as exc:
            logger.error("escalations.create.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(_to_item(rule))

    async def update(
        self,
        rule_id: int,
        req: EscalationRuleUpdateRequest,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[EscalationRuleItem]:
        """エスカレーションルールを更新する。

        Args:
            rule_id: 更新対象のルール ID
            req: 更新リクエスト（product_id は変更不可）
            scope: 組織スコープ

        Returns:
            Ok(EscalationRuleItem): 更新後のルール
            Err(AppError): ルールが見つからない / DB エラー
        """
        try:
            rule = (
                await self._session.execute(
                    select(EscalationRuleOrm)
                    .options(joinedload(EscalationRuleOrm.product))
                    .where(
                        EscalationRuleOrm.id == rule_id,
                        EscalationRuleOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if rule is None:
                return Err(
                    AppError(type="NOT_FOUND", message="指定されたエスカレーションルールが見つかりません")
                )

            now = self._clock.now().replace(tzinfo=None)
            rule.alert_days_before = req.alert_days_before
            rule.escalation_days = req.escalation_days
            rule.is_active = 1 if req.is_active else 0
            rule.updated_at = now
        except Exception as exc:
            logger.error("escalations.update.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(_to_item(rule))

    async def delete(
        self,
        rule_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[None]:
        """エスカレーションルールを論理削除する。

        Args:
            rule_id: 削除対象のルール ID
            scope: 組織スコープ

        Returns:
            Ok(None): 削除成功
            Err(AppError): ルールが見つからない / DB エラー
        """
        try:
            rule = (
                await self._session.execute(
                    select(EscalationRuleOrm).where(
                        EscalationRuleOrm.id == rule_id,
                        EscalationRuleOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if rule is None:
                return Err(
                    AppError(type="NOT_FOUND", message="指定されたエスカレーションルールが見つかりません")
                )

            now = self._clock.now().replace(tzinfo=None)
            rule.delete_flg = 1
            rule.updated_at = now
        except Exception as exc:
            logger.error("escalations.delete.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(None)

    async def bulk_apply(
        self,
        rule_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[BulkApplyResponse]:
        """製品のエスカレーションルールを基に全タスクを即時評価する。

        Phase 6 通知インフラが整うまでは集計サマリーのみを返す（実際の通知は送信しない）。
        # TODO(domain): Phase 6 で通知送信ロジックをここに追加する

        Args:
            rule_id: 評価するルール ID
            scope: 組織スコープ

        Returns:
            Ok(BulkApplyResponse): 評価結果サマリー
            Err(AppError): ルールが見つからない / DB エラー
        """
        try:
            # ルールと製品を取得
            rule = (
                await self._session.execute(
                    select(EscalationRuleOrm).where(
                        EscalationRuleOrm.id == rule_id,
                        EscalationRuleOrm.delete_flg == 0,
                    )
                )
            ).scalar_one_or_none()
            if rule is None:
                return Err(
                    AppError(type="NOT_FOUND", message="指定されたエスカレーションルールが見つかりません")
                )

            today: datetime.date = self._clock.now().date()
            alert_threshold = today + datetime.timedelta(days=rule.alert_days_before)
            escalation_threshold = today - datetime.timedelta(days=rule.escalation_days)

            # アクティブ・未削除タスクを集計
            # NOTE: N+1 を回避するため集計を DB 側で実行する
            base_where = [
                TicketOrm.product_id == rule.product_id,
                TicketOrm.delete_flg == 0,
                TicketOrm.status.notin_(["closed", "rejected"]),
                TicketOrm.due_date.is_not(None),
            ]

            # 期日前アラート対象件数: 今日 ≤ due_date ≤ alert_threshold
            alert_count_result = await self._session.execute(
                select(func.count(TicketOrm.id)).where(
                    *base_where,
                    TicketOrm.due_date >= today,
                    TicketOrm.due_date <= alert_threshold,
                )
            )
            alert_target_count: int = alert_count_result.scalar_one()

            # 期日超過件数: due_date < 今日
            overdue_count_result = await self._session.execute(
                select(func.count(TicketOrm.id)).where(
                    *base_where,
                    TicketOrm.due_date < today,
                )
            )
            overdue_count: int = overdue_count_result.scalar_one()

            # エスカレーション対象件数: due_date ≤ escalation_threshold
            escalation_count_result = await self._session.execute(
                select(func.count(TicketOrm.id)).where(
                    *base_where,
                    TicketOrm.due_date <= escalation_threshold,
                )
            )
            escalation_target_count: int = escalation_count_result.scalar_one()

        except Exception as exc:
            logger.error("escalations.bulk_apply.db_error", exc_info=exc)
            return Err(AppError(type="INTERNAL", message="DB アクセスエラー", details=str(exc)))

        return Ok(
            BulkApplyResponse(
                product_id=rule.product_id,
                rule_id=rule.id,
                alert_target_count=alert_target_count,
                overdue_count=overdue_count,
                escalation_target_count=escalation_target_count,
                evaluated_at=self._clock.now().isoformat(),
            )
        )
