"""タスクグループ Router。

HTTP 入力検証・Result → HTTP 変換・レスポンス整形を担う。
ビジネスロジックは Repository 層に委譲する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.common.logger import get_logger
from app.common.result_to_http import to_http_exception
from app.core.auth.dependencies import get_current_user, permission_required
from app.core.auth.models import AuthenticatedUser
from app.core.clock import Clock, get_clock
from app.core.constants.permissions import Actions, Resources
from app.core.database import get_db
from app.features.task_groups.list.repository import TaskGroupRepository
from app.features.task_groups.list.schemas import (
    TaskGroupAddMembersRequest,
    TaskGroupCreateRequest,
    TaskGroupCreateResponse,
    TaskGroupItem,
    TaskGroupListResponse,
    TaskGroupRemoveMembersRequest,
    TaskGroupUpdateRequest,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(component="task_groups")

router = APIRouter(prefix="/api/v1/task-groups", tags=["task-groups"])


def _get_repository(
    session: AsyncSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> TaskGroupRepository:
    return TaskGroupRepository(session, clock)


# ---- 一覧取得 ---------------------------------------------------------------


@router.get(
    "",
    response_model=TaskGroupListResponse,
    summary="タスクグループ一覧取得",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_task_groups(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupListResponse:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("task_groups.list.request", user_id=user.id, request_id=request_id)

    result = await repository.list_groups(scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- チケット別グループ一覧取得 -----------------------------------------------


@router.get(
    "/by-ticket/{ticket_id}",
    response_model=TaskGroupListResponse,
    summary="チケットが属するグループ一覧",
    dependencies=[permission_required(Actions.READ, Resources.TASK)],
)
async def list_task_groups_for_ticket(
    ticket_id: int,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupListResponse:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("task_groups.by_ticket.request", user_id=user.id, ticket_id=ticket_id, request_id=request_id)

    result = await repository.list_groups_for_ticket(ticket_id=ticket_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- グループ作成 -------------------------------------------------------------


@router.post(
    "",
    response_model=TaskGroupCreateResponse,
    status_code=201,
    summary="タスクグループ作成",
    dependencies=[permission_required(Actions.CREATE, Resources.TASK)],
)
async def create_task_group(
    body: TaskGroupCreateRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupCreateResponse:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "task_groups.create.request",
        user_id=user.id,
        ticket_ids=body.ticket_ids,
        request_id=request_id,
    )

    result = await repository.create(req=body, created_by=user.id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- グループ名・説明更新 ------------------------------------------------------


@router.patch(
    "/{group_id}",
    response_model=TaskGroupItem,
    summary="タスクグループ名・説明更新",
    dependencies=[permission_required(Actions.UPDATE, Resources.TASK)],
)
async def update_task_group(
    group_id: int,
    body: TaskGroupUpdateRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupItem:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("task_groups.update.request", user_id=user.id, group_id=group_id, request_id=request_id)

    result = await repository.update(group_id=group_id, req=body, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- メンバー追加 -------------------------------------------------------------


@router.post(
    "/{group_id}/members",
    response_model=TaskGroupItem,
    summary="グループにチケットを追加",
    dependencies=[permission_required(Actions.UPDATE, Resources.TASK)],
)
async def add_members(
    group_id: int,
    body: TaskGroupAddMembersRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupItem:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "task_groups.add_members.request",
        user_id=user.id,
        group_id=group_id,
        ticket_ids=body.ticket_ids,
        request_id=request_id,
    )

    result = await repository.add_members(group_id=group_id, ticket_ids=body.ticket_ids, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- メンバー削除（グループからチケットを外す） ------------------------------------


@router.delete(
    "/{group_id}/members",
    response_model=TaskGroupItem,
    summary="グループからチケットを削除",
    dependencies=[permission_required(Actions.UPDATE, Resources.TASK)],
)
async def remove_members(
    group_id: int,
    body: TaskGroupRemoveMembersRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> TaskGroupItem:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info(
        "task_groups.remove_members.request",
        user_id=user.id,
        group_id=group_id,
        ticket_ids=body.ticket_ids,
        request_id=request_id,
    )

    result = await repository.remove_members(group_id=group_id, ticket_ids=body.ticket_ids, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return result.value


# ---- グループ論理削除 ---------------------------------------------------------


@router.delete(
    "/{group_id}",
    status_code=204,
    summary="タスクグループ論理削除",
    dependencies=[permission_required(Actions.DELETE, Resources.TASK)],
)
async def delete_task_group(
    group_id: int,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    repository: TaskGroupRepository = Depends(_get_repository),
) -> None:
    request_id: str | None = getattr(request.state, "request_id", None)
    logger.info("task_groups.delete.request", user_id=user.id, group_id=group_id, request_id=request_id)

    result = await repository.delete(group_id=group_id, scope=user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
