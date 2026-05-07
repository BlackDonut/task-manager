---
description: "Pythonのコーディング規約。型ヒント必須・Pydanticバリデーション・Resultパターン・snake_caseファイル名を強制する。"
applyTo: ["**/*.py"]
---

# Python Standards

## コード規約

- Python 3.12 以上を使用
- `Any` 型禁止。`object` または具体的な型を使用
- 全関数の戻り値型ヒントを明示
- Union 型は `Literal` / `TypeAlias` / `TypedDict` で discriminated union を優先
- `raise` ルール:
  - 関数内部（try/except 内補助 raise）: 許容
  - 外部伝播: 禁止。Service で catch → Result 変換
  - Router の HTTPException: 許可
- 非同期関数の戻り値: `Result[T]`
- Magic number 禁止。定数として命名・export
- DTO と Domain 型は分離
- 型の循環参照禁止
- import は絶対パス。相対パス禁止（`__init__.py` 内の re-export のみ例外。`from .service import TaskService` のような機能モジュール内参照も絶対パスを使用する）
- 外部入力は Pydantic でバリデーション（原則: `app/features/<feature>/schemas.py`）
- コメントは「なぜ」を記述。非自明な制約には必須（→ `comment-convention.python.instructions.md`）
- ファイル名: `snake_case.py`
- クラス名: `PascalCase`
- 関数・変数名: `snake_case`
- 定数: `UPPER_SNAKE_CASE`（→ `constants-enums.python.instructions.md`）

### Pydantic スキーマ命名規約

> **理由**: 8 名並行開発で各開発者が独自の命名をすると、スキーマ名からリクエスト/レスポンスの区別がつかず、コード検索・レビューの効率が低下する。

| 種別                       | 命名パターン                   | 例                            |
| -------------------------- | ------------------------------ | ----------------------------- |
| 作成リクエスト             | `Create{Entity}Request`        | `CreateProductRequest`        |
| 更新リクエスト             | `Update{Entity}Request`        | `UpdateTaskRequest`           |
| 一括更新リクエスト         | `BulkUpdate{Entity}Request`    | `BulkUpdateTaskRequest`       |
| 単体レスポンス             | `{Entity}Response`             | `ProductResponse`             |
| 一覧レスポンス             | `{Entity}ListResponse`         | `TaskListResponse`            |
| 一覧レスポンス（カーソル） | `CursorPage[{Entity}Response]` | `CursorPage[ProductResponse]` |
| フィルター                 | `{Entity}FilterParams`         | `TaskFilterParams`            |
| 内部 DTO（Service 間）     | `{Entity}Dto`                  | `ProductDto`                  |

- `Request` / `Response` を必ず末尾に付けること（`ProductInput` / `ProductOutput` は禁止）
- Entity 名は PascalCase の単数形（`Products` ではなく `Product`）

### バリデーション制約の一元化

> **理由**: 同じエンティティを複数画面から更新する際に、画面ごとに制約値が異なるとデータ不整合が発生する。

- 文字数上限・数値範囲・正規表現等の **制約値は定数として `app/core/constants/` に一元定義** する
- `Field(max_length=200)` のように数値を直書きしない。`Field(max_length=TASK_TITLE_MAX_LENGTH)` とする
- 作成・更新・一括更新の各スキーマで **同じフィールドには同じ定数を参照** させる

---

## Result パターン

### 型定義

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Literal

T = TypeVar("T")

ErrorType = Literal[
    "NOT_FOUND",
    "VALIDATION",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "CONFLICT",
    "BUSINESS_RULE",
    "INTERNAL",
]

@dataclass(frozen=True)
class AppError:
    type: ErrorType
    message: str
    details: object | None = None  # ログ用

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    ok: Literal[True] = True

@dataclass(frozen=True)
class Err:
    error: AppError
    ok: Literal[False] = False

Result = Ok[T] | Err
```

### Result 適用範囲

#### 返す: Service / Repository 全メソッド、副作用あり非同期ユーティリティ

#### 返さない: Pydantic モデル、冪等純粋関数、定数・型定義

### 外部ライブラリ例外 → Result

```python
async def fetch_external(url: str) -> Result[dict]:
    try:
        data = await external_lib.fetch(url)
        return Ok(value=data)
    except Exception as e:
        return Err(error=AppError(type="INTERNAL", message="fetch failed", details=str(e)))
```

### Service 内 Result unwrap

`ok == False` は早期リターン。

```python
found = await self.task_repository.find_by_id(task_id)
if not found.ok:
    return found  # 伝播
```

### Router 層での Result 展開

`Result` を受け取り `to_http_exception()` で展開。Service からの raise 伝播は L2 違反。

```python
@router.patch("/{task_id}")
async def update_task(task_id: str, dto: UpdateTaskDto) -> TaskResponse:
    result = await tasks_service.update(task_id, dto)
    if not result.ok:
        raise to_http_exception(result.error)
    return to_task_response(result.value)
```

---

## Pydantic バリデーション

### 適用範囲

#### 必須（外部入力）

- HTTP リクエスト（body / query / path params）
- フォーム入力
- 外部 API レスポンス

#### 対象外

- SQLAlchemy モデル型付き戻り値（ORM 型安全保証）
- FastAPI Depends 検証済み入力
- 型安全な内部関数の引数

### スキーマ定義例

```python
from pydantic import BaseModel, Field

class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

class TaskResponse(BaseModel):
    id: str
    title: str
    status: str

    model_config = {"from_attributes": True}
```

---

## Pydantic スキーマ分割構造

```
app/features/tasks/
    schemas.py     # Task の Request / Response / Filter
app/features/applications/products/
    schemas.py     # Product の Request / Response
app/features/applications/
    schemas.py     # Application の Request / Response
app/common/
    schemas.py     # 共通型（ID・日付・ページネーション等）
```

---

## Linter・Formatter

- Ruff（Lint + Format）を使用
- mypy（型チェック）を使用
- `pyproject.toml` に設定を集約

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "S", "T20"]

[tool.mypy]
python_version = "3.12"
strict = true
disallow_any_explicit = true
```
