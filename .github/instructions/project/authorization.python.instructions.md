---
description: "認可（RBAC/ABAC）の実装規約。Depends認可・Permission定義・組織スコープ・テストパターンを強制する。"
applyTo: "**/*.py"
---

# Authorization Standards

## L1 ルール

- 保護リソースへのエンドポイントに `permission_required` Depends なしは禁止（`copilot-instructions.md` §L1 と統一）
- `Depends(get_current_user)` なしの保護エンドポイントは禁止
- Repository で `OrganizationScope` 引数なしのクエリは禁止

## L2 ルール

- 認可をバイパスする `@public` デコレータ使用時は ADR + セキュリティレビュー必須
- テストで認可チェックの正常/拒否の両方をカバーしていない場合は警告
- WebSocket イベント送信時に認可チェックを省略する場合は警告

## 実装パターン

### Router

```python
@router.patch("/{task_id}", dependencies=[permission_required(Actions.UPDATE, Resources.TASK)])
async def update_task(
    task_id: str,
    dto: UpdateTaskRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    # permission_required が Role → Permission を自動検証
    result = await service.update(task_id, dto, user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return TaskResponse.model_validate(result.value)
```

### Service

```python
# scope は全メソッド引数に含める（省略不可）
async def find_all(
    self,
    filters: TaskFilterInput,
    scope: OrganizationScope,
) -> Result[list[Task]]:
    return await self.repository.find_many(filters, scope)
```

### Repository

```python
# OrganizationScope でデータスコープ強制
async def find_many(
    self,
    where: TaskWhereInput,
    scope: OrganizationScope,
) -> Result[list[Task]]:
    stmt = (
        select(Task)
        .where(
            Task.organization_id == scope.organization_id,
            Task.delete_flg == 0,
        )
    )
    result = await self.session.execute(stmt)
    return Ok(value=list(result.scalars().all()))
```

### テスト

テストでは以下の **3 パターンを必須**とする（欠如は L2 違反）：

1. **権限あり**: 正常にリソースにアクセスできること
2. **権限なし**: 403 Forbidden が返ること
3. **組織外**: 他組織のリソースにアクセスできないこと

## 参照

- API 設計: `.github/instructions/project/api-design.instructions.md`
