"""タスクグループ Repository（SQL Server 実装）。

DB: SQL Server / SQLAlchemy async (aioodbc)
画面: SCR-T001（チケット一覧 グループ管理ダイアログ）
業務制約:
  - delete_flg == 0 のグループのみ返す
  - 論理削除済みチケットはメンバー一覧に含めない
  - メンバー追加時の重複は UNIQUE 制約でガードし、アプリ層で冪等に処理する
  - datetime.now() 直接使用禁止: Clock ファクトリで時刻を取得する（L2）
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.logger import get_logger
from app.core.auth.models import OrganizationScope
from app.core.clock import SystemClock
from app.core.result import AppError, Err, Ok, Result
from app.features.task_groups.list.schemas import (
    GroupMemberSummary,
    TaskGroupCreateRequest,
    TaskGroupCreateResponse,
    TaskGroupItem,
    TaskGroupListResponse,
    TaskGroupUpdateRequest,
)
from app.models.task_group import TaskGroupOrm, TicketGroupMemberOrm
from app.models.ticket import TicketOrm

logger = get_logger(component="task_groups.repository")


class TaskGroupRepository:
    """タスクグループのデータアクセス（SQL Server 実装）。"""

    def __init__(self, session: AsyncSession, clock: SystemClock | None = None) -> None:
        self._session = session
        self._clock = clock if clock is not None else SystemClock()

    # ------------------------------------------------------------------
    # 一覧取得
    # ------------------------------------------------------------------

    async def list_groups(
        self,
        scope: OrganizationScope,  # noqa: ARG002 — 将来マルチテナント対応時に使用
    ) -> Result[TaskGroupListResponse]:
        """論理削除されていないタスクグループ一覧を返す。"""
        try:
            stmt = (
                select(TaskGroupOrm)
                .where(TaskGroupOrm.delete_flg == 0)
                .options(
                    selectinload(TaskGroupOrm.members).selectinload(
                        TicketGroupMemberOrm.group  # back_populate 経由の型解決
                    )
                )
                .order_by(TaskGroupOrm.created_at.desc())
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()

            items = [await self._to_item(g) for g in rows]
            return Ok(TaskGroupListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("task_groups.list.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="タスクグループ一覧の取得に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # グループ作成
    # ------------------------------------------------------------------

    async def create(
        self,
        req: TaskGroupCreateRequest,
        created_by: int | None,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[TaskGroupCreateResponse]:
        """タスクグループを作成し、指定チケットをメンバーとして登録する。"""
        try:
            now = self._clock.now()

            # --- チケット存在確認 ---
            for tid in req.ticket_ids:
                t = await self._session.get(TicketOrm, tid)
                if t is None or t.delete_flg != 0:
                    return Err(AppError(
                        type="NOT_FOUND",
                        message=f"チケット ID={tid} が見つかりません",
                    ))

            # --- グループ本体作成 ---
            group = TaskGroupOrm(
                name=req.name,
                description=req.description,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            self._session.add(group)
            await self._session.flush()  # group.id を確定させる

            # --- メンバー追加 ---
            members: list[TicketGroupMemberOrm] = []
            for tid in req.ticket_ids:
                member = TicketGroupMemberOrm(
                    group_id=group.id,
                    ticket_id=tid,
                    added_at=now,
                )
                self._session.add(member)
                members.append(member)

            await self._session.flush()

            # --- レスポンス生成: チケット情報を別途取得 ---
            member_summaries = await self._load_member_summaries(req.ticket_ids, now.isoformat())

            await self._session.commit()
            logger.info("task_groups.create", group_id=group.id, ticket_ids=req.ticket_ids)

            return Ok(TaskGroupCreateResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                members=member_summaries,
            ))

        except Exception as exc:
            await self._session.rollback()
            logger.error("task_groups.create.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="タスクグループの作成に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # グループ名・説明の更新
    # ------------------------------------------------------------------

    async def update(
        self,
        group_id: int,
        req: TaskGroupUpdateRequest,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[TaskGroupItem]:
        """グループ名・説明を更新する。メンバー変更は add_members / remove_members を使用。"""
        try:
            group = await self._session.get(TaskGroupOrm, group_id)
            if group is None or group.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"タスクグループ ID={group_id} が見つかりません"))

            group.name = req.name
            group.description = req.description
            group.updated_at = self._clock.now()
            await self._session.flush()

            item = await self._to_item(group)
            await self._session.commit()
            logger.info("task_groups.update", group_id=group_id)
            return Ok(item)

        except Exception as exc:
            await self._session.rollback()
            logger.error("task_groups.update.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="タスクグループの更新に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # メンバー追加
    # ------------------------------------------------------------------

    async def add_members(
        self,
        group_id: int,
        ticket_ids: list[int],
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[TaskGroupItem]:
        """指定チケットをグループに追加する。既に登録済みの場合は冪等にスキップする。"""
        try:
            group = await self._session.get(TaskGroupOrm, group_id)
            if group is None or group.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"タスクグループ ID={group_id} が見つかりません"))

            now = self._clock.now()

            for tid in ticket_ids:
                t = await self._session.get(TicketOrm, tid)
                if t is None or t.delete_flg != 0:
                    return Err(AppError(type="NOT_FOUND", message=f"チケット ID={tid} が見つかりません"))

                # 既存メンバーかどうかを確認（重複は冪等にスキップ）
                exists_stmt = select(TicketGroupMemberOrm).where(
                    TicketGroupMemberOrm.group_id == group_id,
                    TicketGroupMemberOrm.ticket_id == tid,
                )
                existing = (await self._session.execute(exists_stmt)).scalar_one_or_none()
                if existing is None:
                    self._session.add(TicketGroupMemberOrm(
                        group_id=group_id,
                        ticket_id=tid,
                        added_at=now,
                    ))

            group.updated_at = now
            await self._session.flush()

            item = await self._to_item(group)
            await self._session.commit()
            logger.info("task_groups.add_members", group_id=group_id, ticket_ids=ticket_ids)
            return Ok(item)

        except Exception as exc:
            await self._session.rollback()
            logger.error("task_groups.add_members.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="メンバーの追加に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # メンバー削除
    # ------------------------------------------------------------------

    async def remove_members(
        self,
        group_id: int,
        ticket_ids: list[int],
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[TaskGroupItem]:
        """指定チケットをグループから削除する。グループ解散（全員削除）も許容する。"""
        try:
            group = await self._session.get(TaskGroupOrm, group_id)
            if group is None or group.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"タスクグループ ID={group_id} が見つかりません"))

            await self._session.execute(
                delete(TicketGroupMemberOrm).where(
                    TicketGroupMemberOrm.group_id == group_id,
                    TicketGroupMemberOrm.ticket_id.in_(ticket_ids),
                )
            )
            group.updated_at = self._clock.now()
            await self._session.flush()

            item = await self._to_item(group)
            await self._session.commit()
            logger.info("task_groups.remove_members", group_id=group_id, ticket_ids=ticket_ids)
            return Ok(item)

        except Exception as exc:
            await self._session.rollback()
            logger.error("task_groups.remove_members.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="メンバーの削除に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # グループ論理削除
    # ------------------------------------------------------------------

    async def delete(
        self,
        group_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[None]:
        """タスクグループを論理削除する。メンバーレコードは物理的に残す（監査証跡）。"""
        try:
            group = await self._session.get(TaskGroupOrm, group_id)
            if group is None or group.delete_flg != 0:
                return Err(AppError(type="NOT_FOUND", message=f"タスクグループ ID={group_id} が見つかりません"))

            group.delete_flg = 1
            group.updated_at = self._clock.now()
            await self._session.commit()
            logger.info("task_groups.delete", group_id=group_id)
            return Ok(None)

        except Exception as exc:
            await self._session.rollback()
            logger.error("task_groups.delete.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="タスクグループの削除に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # チケット所属グループ一覧取得（チケット編集ダイアログ用）
    # ------------------------------------------------------------------

    async def list_groups_for_ticket(
        self,
        ticket_id: int,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[TaskGroupListResponse]:
        """指定チケットが属するグループ一覧を返す。"""
        try:
            stmt = (
                select(TaskGroupOrm)
                .join(TicketGroupMemberOrm, TicketGroupMemberOrm.group_id == TaskGroupOrm.id)
                .where(
                    TicketGroupMemberOrm.ticket_id == ticket_id,
                    TaskGroupOrm.delete_flg == 0,
                )
                .order_by(TaskGroupOrm.created_at.desc())
            )
            rows = (await self._session.execute(stmt)).unique().scalars().all()
            items = [await self._to_item(g) for g in rows]
            return Ok(TaskGroupListResponse(items=items, total=len(items)))
        except Exception as exc:
            logger.error("task_groups.list_for_ticket.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="グループ一覧の取得に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # 自動完了: チケット完了時に同グループの未完了チケットを全件完了させる
    # ------------------------------------------------------------------

    async def propagate_completion(
        self,
        completed_ticket_id: int,
        new_status: str,
        scope: OrganizationScope,  # noqa: ARG002
    ) -> Result[list[int]]:
        """グループ内の未完了チケットをすべて new_status に更新する。

        チケット更新 Repository からトランザクション内で呼び出す想定。
        Session.commit() は呼び出し元で行う。本メソッドは flush のみ行う。

        Args:
            completed_ticket_id: 完了したチケット ID
            new_status: 伝播するステータス（"closed" または "resolved"）
            scope: 組織スコープ

        Returns:
            Ok(list[int]): 自動完了させたチケット ID リスト（0 件の場合は空リスト）
            Err(AppError): DB エラー時
        """
        _COMPLETION_STATUSES = frozenset({"closed", "resolved"})
        if new_status not in _COMPLETION_STATUSES:
            # 完了ステータス以外では伝播しない
            return Ok([])

        try:
            now = self._clock.now()

            # 対象チケットが属するグループ ID を全取得
            group_id_stmt = select(TicketGroupMemberOrm.group_id).where(
                TicketGroupMemberOrm.ticket_id == completed_ticket_id
            )
            group_ids = list((await self._session.execute(group_id_stmt)).scalars().all())
            if not group_ids:
                return Ok([])

            # 各グループの未完了メンバーチケット ID を収集
            member_stmt = (
                select(TicketGroupMemberOrm.ticket_id)
                .join(TaskGroupOrm, TaskGroupOrm.id == TicketGroupMemberOrm.group_id)
                .where(
                    TicketGroupMemberOrm.group_id.in_(group_ids),
                    TicketGroupMemberOrm.ticket_id != completed_ticket_id,
                    TaskGroupOrm.delete_flg == 0,
                )
            )
            sibling_ticket_ids = list((await self._session.execute(member_stmt)).scalars().all())
            if not sibling_ticket_ids:
                return Ok([])

            # 未完了チケットを取得して完了ステータスに更新
            updated_ids: list[int] = []
            for tid in sibling_ticket_ids:
                ticket = await self._session.get(TicketOrm, tid)
                if ticket is None or ticket.delete_flg != 0:
                    continue
                if ticket.status in _COMPLETION_STATUSES:
                    continue  # 既に完了済みはスキップ
                ticket.status = new_status
                ticket.updated_at = now
                updated_ids.append(tid)

            if updated_ids:
                await self._session.flush()
                logger.info(
                    "task_groups.propagate_completion",
                    trigger_ticket_id=completed_ticket_id,
                    propagated_to=updated_ids,
                    new_status=new_status,
                )

            return Ok(updated_ids)

        except Exception as exc:
            logger.error("task_groups.propagate_completion.error", error=str(exc))
            return Err(AppError(type="INTERNAL", message="グループ内チケットの自動完了に失敗しました", details=exc))

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    async def _to_item(self, group: TaskGroupOrm) -> TaskGroupItem:
        """TaskGroupOrm → TaskGroupItem 変換。メンバーのチケット情報を JOIN で補完する。"""
        # メンバーレコードのチケット ID を収集（論理削除済みメンバー行は常に存在しない前提）
        member_stmt = (
            select(TicketGroupMemberOrm, TicketOrm)
            .join(TicketOrm, TicketOrm.id == TicketGroupMemberOrm.ticket_id)
            .where(
                TicketGroupMemberOrm.group_id == group.id,
                TicketOrm.delete_flg == 0,
            )
            .order_by(TicketGroupMemberOrm.added_at)
        )
        rows = (await self._session.execute(member_stmt)).all()

        members: list[GroupMemberSummary] = []
        for member_orm, ticket_orm in rows:
            # 製品名は product リレーションをロード済みか確認してから取得
            product_name = ""
            if ticket_orm.product_id:
                from app.models.product import ProductOrm  # noqa: PLC0415
                product = await self._session.get(ProductOrm, ticket_orm.product_id)
                product_name = product.name if product else ""

            members.append(GroupMemberSummary(
                ticket_id=ticket_orm.id,
                subject=ticket_orm.subject,
                status=ticket_orm.status,
                product_name=product_name,
                added_at=member_orm.added_at.isoformat(),
            ))

        return TaskGroupItem(
            id=group.id,
            name=group.name,
            description=group.description,
            member_count=len(members),
            members=members,
        )

    async def _load_member_summaries(
        self, ticket_ids: list[int], added_at_iso: str
    ) -> list[GroupMemberSummary]:
        """チケット ID リストからメンバーサマリーリストを生成する（作成直後用）。"""
        summaries: list[GroupMemberSummary] = []
        for tid in ticket_ids:
            ticket = await self._session.get(TicketOrm, tid)
            if ticket is None:
                continue
            from app.models.product import ProductOrm  # noqa: PLC0415
            product = await self._session.get(ProductOrm, ticket.product_id)
            summaries.append(GroupMemberSummary(
                ticket_id=ticket.id,
                subject=ticket.subject,
                status=ticket.status,
                product_name=product.name if product else "",
                added_at=added_at_iso,
            ))
        return summaries
