"""エスカレーションルール Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Repository 層に委譲する。

セキュリティ:
  - 全エンドポイントに permission_required を付与する（L1）
  - CRUD: Actions.MANAGE / Resources.ESCALATION_RULE
  - 一覧取得: Actions.READ / Resources.ESCALATION_RULE
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.clock import Clock, get_clock
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.notifications.escalations.repository import EscalationRuleRepository
from app.features.notifications.escalations.schemas import (
    BulkApplyResponse,
    EscalationRuleCreateRequest,
    EscalationRuleItem,
    EscalationRuleListResponse,
    EscalationRuleUpdateRequest,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="escalations")

router = APIRouter(prefix="/api/v1/escalation-rules", tags=["escalation-rules"])


def _get_repository(
    session: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> EscalationRuleRepository:
    """依存性注入: DB セッション + Clock を受け取り Repository を構築して返す。"""
    return EscalationRuleRepository(session, clock)


@router.get(
    "",
    response_model=EscalationRuleListResponse,
    summary="エスカレーションルール一覧取得",
    description="product_id を指定するとその製品のルールのみ返す。",
    dependencies=[permission_required(Actions.READ, Resources.ESCALATION_RULE)],
)
async def list_escalation_rules(
    request: Request,
    product_id: int | None = Query(default=None, description="製品 ID で絞り込み"),
    user: AuthenticatedUser = Depends(get_current_user),
    repository: EscalationRuleRepository = Depends(_get_repository),
) -> EscalationRuleListResponse:
    """エスカレーションルール一覧を返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "escalations.list.request",
        user_id=user.id,
        product_id=product_id,
        request_id=request_id,
    )

    result = await repository.get_list(product_id=product_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "escalations.list.response",
        user_id=user.id,
        total=result.value.total,
        request_id=request_id,
    )
    return result.value


@router.post(
    "",
    response_model=EscalationRuleItem,
    status_code=201,
    summary="エスカレーションルール作成",
    description="製品にアラートルール（期日前通知日数・エスカレーション遅延日数）を設定する。1 製品につき 1 ルールのみ作成可能。",
    dependencies=[permission_required(Actions.MANAGE, Resources.ESCALATION_RULE)],
)
async def create_escalation_rule(
    request: Request,
    body: EscalationRuleCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: EscalationRuleRepository = Depends(_get_repository),
) -> EscalationRuleItem:
    """エスカレーションルールを作成する。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "escalations.create.request",
        user_id=user.id,
        product_id=body.product_id,
        request_id=request_id,
    )

    result = await repository.create(req=body, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "escalations.create.response",
        user_id=user.id,
        rule_id=result.value.id,
        request_id=request_id,
    )
    return result.value


@router.patch(
    "/{rule_id}",
    response_model=EscalationRuleItem,
    summary="エスカレーションルール更新",
    description="既存ルールの条件値（日数・有効/無効）を更新する。product_id は変更不可。",
    dependencies=[permission_required(Actions.MANAGE, Resources.ESCALATION_RULE)],
)
async def update_escalation_rule(
    request: Request,
    rule_id: int,
    body: EscalationRuleUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: EscalationRuleRepository = Depends(_get_repository),
) -> EscalationRuleItem:
    """エスカレーションルールを更新する。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "escalations.update.request",
        user_id=user.id,
        rule_id=rule_id,
        request_id=request_id,
    )

    result = await repository.update(rule_id=rule_id, req=body, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "escalations.update.response",
        user_id=user.id,
        rule_id=rule_id,
        request_id=request_id,
    )
    return result.value


@router.delete(
    "/{rule_id}",
    status_code=204,
    summary="エスカレーションルール削除",
    description="論理削除。削除後、対象製品のタスクはアラート対象外となる。",
    dependencies=[permission_required(Actions.MANAGE, Resources.ESCALATION_RULE)],
)
async def delete_escalation_rule(
    request: Request,
    rule_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: EscalationRuleRepository = Depends(_get_repository),
) -> None:
    """エスカレーションルールを論理削除する。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "escalations.delete.request",
        user_id=user.id,
        rule_id=rule_id,
        request_id=request_id,
    )

    result = await repository.delete(rule_id=rule_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "escalations.delete.response",
        user_id=user.id,
        rule_id=rule_id,
        request_id=request_id,
    )


@router.post(
    "/{rule_id}/bulk-apply",
    response_model=BulkApplyResponse,
    summary="一括適用（即時評価）",
    description=(
        "製品に紐づくエスカレーションルールを基に、全アクティブタスクを即時評価する。"
        " 期日前アラート対象・期日超過・エスカレーション対象の件数サマリーを返す。"
        " Phase 6 通知インフラが整い次第、実際の通知送信もここで実行する予定。"
    ),
    dependencies=[permission_required(Actions.MANAGE, Resources.ESCALATION_RULE)],
)
async def bulk_apply_escalation_rule(
    request: Request,
    rule_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: EscalationRuleRepository = Depends(_get_repository),
) -> BulkApplyResponse:
    """製品の全タスクをエスカレーションルールで即時評価し、サマリーを返す。"""
    request_id: str | None = getattr(request.state, "request_id", None)

    logger.info(
        "escalations.bulk_apply.request",
        user_id=user.id,
        rule_id=rule_id,
        request_id=request_id,
    )

    result = await repository.bulk_apply(rule_id=rule_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error, request_id)

    logger.info(
        "escalations.bulk_apply.response",
        user_id=user.id,
        rule_id=rule_id,
        alert_target_count=result.value.alert_target_count,
        escalation_target_count=result.value.escalation_target_count,
        request_id=request_id,
    )
    return result.value
