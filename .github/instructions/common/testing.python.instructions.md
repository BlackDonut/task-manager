---
description: "pytestのテスト規約と生成。AAA構造・モック戦略・Pydantic/FastAPI/純粋関数のテストパターン・テストデータへのPII禁止をカバーする。"
applyTo: ["**/test_*.py", "**/tests/**/*.py"]
---

# Test Standards

## 基本ルール

- フレームワーク: pytest + pytest-asyncio
- 構造: Arrange / Act / Assert
- テスト説明文: 「〜の場合、〜になる」形式
- `print()` 禁止
- 1 テスト = 1 論理アサーション（検証対象の振る舞いが 1 つであること。同じ振る舞いの複数属性を確認する `assert` 文は許容する。L3 ルール）

## テストデータ

- PII 禁止。ダミー値は英数字（`"user-001"`, `"task-abc"`）

## mock 戦略

- 純粋関数: モックなし
- 副作用あり（DB・HTTP・タイマー）: mock 使用（`unittest.mock` / `pytest-mock`）

## 生成の優先順位

1. 副作用確認 → あれば mock
2. 境界値・エラーケースを正常系より先に設計
3. 1 テスト = 1 アサーション

## AAA 構造例

```python
def test_タイトルが空の場合バリデーションエラーになる():
    # Arrange
    input_data = {"title": "", "due_date": "2026-04-10"}

    # Act
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskRequest(**input_data)

    # Assert
    assert "title" in str(exc_info.value)
```

---

## テスト種別ルール

### Pydantic スキーマ

- 正常系・異常系（型不正・必須欠落・境界値）の両方テスト
- `model_validate` / コンストラクタで検証

### FastAPI Router

- Router / Service を分けてテスト
- Service 依存はモック
- Router: HTTP レスポンスコードと Result→例外変換を検証
- `httpx.AsyncClient` + `app.dependency_overrides` でテスト

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_タスク作成が正常に完了する():
    # Arrange
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Act
        response = await client.post("/api/v1/tasks", json={"title": "task-001"})

    # Assert
    assert response.status_code == 201
```

### 純粋関数

- モックなし・入力→出力を網羅

---

## 一括操作テスト（BulkUpdateService）

→ テストパターン詳細は [`bulk-operation.python.instructions.md`](bulk-operation.python.instructions.md) を参照。

---

## ディレクトリ構造

> `app/features/` のドメイングループ → サブ機能構造をミラーする。

```
tests/
├── conftest.py                          # 共通フィクスチャ
├── unit/
│   ├── features/                        # ドメイングループミラー
│   │   ├── <domain>/
│   │   │   ├── test_crud_service.py     # <domain>/crud/service.py のテスト
│   │   │   ├── test_crud_repository.py
│   │   │   └── test_<sub>_service.py   # サブ機能ごとに追加
│   │   └── ...
│   ├── schemas/
│   └── common/
├── integration/
│   └── features/                        # Router 統合テスト（同ミラー構造）
│       ├── <domain>/
│       │   └── test_<sub>_router.py
│       └── ...
└── e2e/
    └── ...
```

## フィクスチャの分割ルール

> **理由**: 全テストが 1 つの巨大な `conftest.py` に依存すると、1 変更で大量のテストが壊れる。

- `tests/conftest.py`: DB セッション・認証モック等の **インフラ系フィクスチャのみ**
- `tests/unit/features/<domain>/conftest.py`: そのドメイン固有のフィクスチャ
- テストデータは **ファクトリ関数** で生成する。グローバルフィクスチャにテストデータを定義しない

```python
# tests/factories.py（または各ドメインの conftest.py）
def build_task(**overrides: object) -> dict[str, object]:
    """テスト用タスクデータを生成する。overrides で任意のフィールドを上書き可能。"""
    defaults: dict[str, object] = {
        "id": "task-test-001",
        "title": "test-task",
        "status": "not_started",
    }
    return {**defaults, **overrides}
```
