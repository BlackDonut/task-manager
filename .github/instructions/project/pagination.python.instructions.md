---
description: "ページネーションの実装規約。Cursor-based pagination の標準実装・共通型定義を定義する。"
applyTo: "**/*.py"
---

# Pagination Standards

## L2 ルール

- ページネーションなしで一覧 API を作成する場合は警告

## 型名の SSOT

> 型名は `app/core/schemas/pagination.py` が SSOT。以下の名称を必ず使用する。

| 用途                        | 型名                     |
| --------------------------- | ------------------------ |
| ページネーション レスポンス | `CursorPage[T]`          |
| ページネーション リクエスト | `CursorPaginationParams` |
| Repository 戻り値           | `CursorPage[Entity]`     |

## 実装パターン

### バックエンド: Router

```python
from app.core.schemas.pagination import CursorPage, CursorPaginationParams

@router.get("/", response_model=CursorPage[TaskResponse])
async def find_all(
    params: CursorPaginationParams = Depends(),
    user: AuthenticatedUser = Depends(get_current_user),
    service: TasksService = Depends(get_tasks_service),
) -> CursorPage[TaskResponse]:
    return await service.find_all(params, user.scope)
```

### バックエンド: Repository

```python
from app.common.cursor_pagination import decode_cursor, build_cursor_page
from app.core.schemas.pagination import CursorPage, CursorPaginationParams

async def find_many(
    self,
    params: CursorPaginationParams,
    scope: OrganizationScope,
) -> Result[CursorPage[Task]]:
    stmt = (
        select(Task)
        .where(
            Task.organization_id == scope.organization_id,
            Task.delete_flg == 0,
        )
        # カーソルは UUID v7 の id 列を基準にする（[ADR-0002] 参照）
        # sort_by を変更する場合は ADR を起こして変更すること
        .order_by(Task.id.asc())
        .limit(params.limit + 1)  # 次ページ存在チェック用に 1 件余分に取得
    )
    if params.cursor:
        cursor_result = decode_cursor(params.cursor)
        if isinstance(cursor_result, Err):
            return cursor_result
        decoded_id = cursor_result.value
        if decoded_id is not None:
            stmt = stmt.where(Task.id > decoded_id)

    result = self.session.execute(stmt)
    items = list(result.scalars().all())

    return Ok(value=build_cursor_page(items, params.limit))
```

> **注意**: `decode_cursor` は `Result[str | None]` を返す。`Err` の場合はそのまま上位に返すこと（例外は投げない）。

### 共通型定義（参照のみ・変更禁止）

```python
# app/core/schemas/pagination.py（SSOT）
class CursorPaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    sort_by: str | None = None
    sort_dir: str = Field(default="asc", pattern="^(asc|desc)$")

class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
```

## 参照

- カーソル実装詳細: `app/common/cursor_pagination.py`
