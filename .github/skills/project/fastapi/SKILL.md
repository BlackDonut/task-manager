---
name: fastapi
description: "FastAPIの実装パターン：Router/Service/Repositoryレイヤー・Depends DI・Pydanticバリデーション・ミドルウェア・エラーハンドリング。APIエンドポイントの実装・DI設計・ミドルウェア設定の実装時に使用する。"
applyTo: "app/features/**/*.py"
---

# FastAPI Skill

基本ルールは `api-design.instructions.md` を参照。

---

## レイヤー構造

> 各レイヤーの責務境界は [project-structure.instructions.md](../../instructions/project/project-structure.instructions.md) を参照。

各機能は `router` / `service` / `repository` / `models` / `schemas` の5層に分離する。

---

## Router（Controller 相当）

```python
from fastapi import APIRouter, Depends, HTTPException
from app.features.tasks.schemas import CreateTaskRequest, TaskResponse
from app.features.tasks.service import TasksService
from app.core.auth.dependencies import get_current_user
from app.common.result_to_http import to_http_exception

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(
    dto: CreateTaskRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    result = service.create(dto, user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return TaskResponse.model_validate(result.value)
```

---

## DI（Dependency Injection）

FastAPI の `Depends` を使用。

```python
# app/core/dependencies/tasks.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_session
from app.features.tasks.repository import TasksRepository
from app.features.tasks.service import TasksService
from app.core.clock import Clock, SystemClock

def get_clock() -> Clock:
    return SystemClock()

def get_tasks_repository(
    session: Session = Depends(get_session),
) -> TasksRepository:
    return TasksRepository(session)

def get_tasks_service(
    repo: TasksRepository = Depends(get_tasks_repository),
    clock: Clock = Depends(get_clock),
) -> TasksService:
    return TasksService(repo, clock)
```

---

## エラーハンドリング

```python
# app/common/result_to_http.py
from fastapi import HTTPException, status
from app.core.result import AppError

ERROR_STATUS_MAP: dict[str, int] = {
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "VALIDATION": status.HTTP_400_BAD_REQUEST,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "BUSINESS_RULE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INTERNAL": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

def to_http_exception(error: AppError) -> HTTPException:
    status_code = ERROR_STATUS_MAP.get(error.type, 500)
    # 内部情報を含めない
    detail = error.message if error.type != "INTERNAL" else "Internal server error"
    return HTTPException(status_code=status_code, detail=detail)
```

---

## ミドルウェア

```python
# app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## ヘルスチェック

```python
@router.get("/health")
def health_check(
    session: Session = Depends(get_session),
) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}
```

---

## WebSocket

→ WebSocket の実装パターンは [`instructions/realtime.python.instructions.md`](../../instructions/realtime.python.instructions.md) を参照。

---

## セキュリティ考慮

→ 認証・認可・入力バリデーション・ CORS の詳細は [`instructions/api-design.instructions.md`](../../instructions/api-design.instructions.md) を参照。

---

## スキャフォールドテンプレート

> `scaffold` agent / `/scaffold` プロンプトが参照するひな形コード。
> 生成ルール（認可チェック・OrganizationScope・Result パターン等の必須要件）は
> [`agents/scaffold.agent.md`](../../agents/scaffold.agent.md) §生成ルール を参照。

### router.py

```python
# app/features/<feature>/router.py
from fastapi import APIRouter, Depends, status
from app.core.auth.guards import permission_required, get_current_user
from app.core.database import get_session
from app.common.result_to_http import to_http_exception
from .service import <Feature>Service
from .schemas import (
    <Feature>CreateRequest,
    <Feature>UpdateRequest,
    <Feature>Response,
    <Feature>ListResponse,
)
from .dependencies import get_<feature>_service

router = APIRouter(prefix="/api/v1/<features>", tags=["<features>"])


@router.get("", response_model=<Feature>ListResponse)
def list_<features>(
    # TODO(security): 認可チェック - requires review before check-in
    current_user=Depends(permission_required("<feature>:read")),
    service: <Feature>Service = Depends(get_<feature>_service),
) -> <Feature>ListResponse:
    result = service.list(scope=current_user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return <Feature>ListResponse.model_validate({"items": result.value})


@router.post("", response_model=<Feature>Response, status_code=status.HTTP_201_CREATED)
def create_<feature>(
    dto: <Feature>CreateRequest,
    # TODO(security): 認可チェック - requires review before check-in
    current_user=Depends(permission_required("<feature>:create")),
    service: <Feature>Service = Depends(get_<feature>_service),
) -> <Feature>Response:
    result = service.create(dto, scope=current_user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return <Feature>Response.model_validate(result.value)


@router.patch("/{<feature>_id}", response_model=<Feature>Response)
def update_<feature>(
    <feature>_id: str,
    dto: <Feature>UpdateRequest,
    # TODO(security): 認可チェック - requires review before check-in
    current_user=Depends(permission_required("<feature>:update")),
    service: <Feature>Service = Depends(get_<feature>_service),
) -> <Feature>Response:
    result = service.update(<feature>_id, dto, scope=current_user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return <Feature>Response.model_validate(result.value)


@router.delete("/{<feature>_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_<feature>(
    <feature>_id: str,
    # TODO(security): 認可チェック - requires review before check-in
    current_user=Depends(permission_required("<feature>:delete")),
    service: <Feature>Service = Depends(get_<feature>_service),
) -> None:
    result = service.delete(<feature>_id, scope=current_user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
```

### service.py

```python
# app/features/<feature>/service.py
from app.core.result import Result, Ok, Err, AppError
from app.core.clock import Clock
from app.core.types.auth import OrganizationScope
from .repository import <Feature>Repository
from .schemas import <Feature>CreateRequest, <Feature>UpdateRequest
from .models import <Feature>


class <Feature>Service:
    """<Feature> の業務ロジックを担当する Service."""

    def __init__(self, repo: <Feature>Repository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def list(self, *, scope: OrganizationScope) -> Result[list[<Feature>]]:
        return self._repo.find_all(scope=scope)

    def create(
        self, dto: <Feature>CreateRequest, *, scope: OrganizationScope
    ) -> Result[<Feature>]:
        entity = <Feature>(
            **dto.model_dump(),
            organization_id=scope.organization_id,
            created_at=self._clock.now(),
        )
        return self._repo.save(entity)

    def update(
        self, entity_id: str, dto: <Feature>UpdateRequest, *, scope: OrganizationScope
    ) -> Result[<Feature>]:
        get_result = self._repo.find_by_id(entity_id, scope=scope)
        if not get_result.ok:
            return get_result
        entity = get_result.value
        for field, value in dto.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        return self._repo.save(entity)

    def delete(self, entity_id: str, *, scope: OrganizationScope) -> Result[None]:
        get_result = self._repo.find_by_id(entity_id, scope=scope)
        if not get_result.ok:
            return get_result
        # 論理削除（delete_flg = 1）
        return self._repo.soft_delete(entity_id)
```

### repository.py

```python
# app/features/<feature>/repository.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.result import Result, Ok, Err, AppError
from app.core.types.auth import OrganizationScope
from .models import <Feature>


class <Feature>Repository:
    """<Feature> の DB アクセスを担当する Repository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(self, *, scope: OrganizationScope) -> Result[list[<Feature>]]:
        stmt = (
            select(<Feature>)
            .where(
                <Feature>.organization_id == scope.organization_id,
                <Feature>.delete_flg == 0,  # 論理削除済みを除外（L1 必須）
            )
        )
        rows = self._session.execute(stmt).scalars().all()
        return Ok(value=list(rows))

    def find_by_id(
        self, entity_id: str, *, scope: OrganizationScope
    ) -> Result[<Feature>]:
        stmt = (
            select(<Feature>)
            .where(
                <Feature>.id == entity_id,
                <Feature>.organization_id == scope.organization_id,
                <Feature>.delete_flg == 0,
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return Err(error=AppError(type="NOT_FOUND", message="<Feature> not found"))
        return Ok(value=row)

    def save(self, entity: <Feature>) -> Result[<Feature>]:
        self._session.add(entity)
        self._session.flush()
        return Ok(value=entity)

    def soft_delete(self, entity_id: str) -> Result[None]:
        stmt = (
            select(<Feature>)
            .where(<Feature>.id == entity_id, <Feature>.delete_flg == 0)
        )
        entity = self._session.execute(stmt).scalar_one_or_none()
        if entity is None:
            return Err(error=AppError(type="NOT_FOUND", message="<Feature> not found"))
        entity.delete_flg = 1
        return Ok(value=None)
```

### dependencies.py

```python
# app/features/<feature>/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_session
from app.core.clock import Clock, SystemClock
from .repository import <Feature>Repository
from .service import <Feature>Service


def get_clock() -> Clock:
    return SystemClock()


def get_<feature>_repository(
    session: Session = Depends(get_session),
) -> <Feature>Repository:
    return <Feature>Repository(session)


def get_<feature>_service(
    repo: <Feature>Repository = Depends(get_<feature>_repository),
    clock: Clock = Depends(get_clock),
) -> <Feature>Service:
    return <Feature>Service(repo, clock)
```
