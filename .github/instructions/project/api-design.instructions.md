---
description: "FastAPI APIの設計。レイヤーの責務・Result→HTTP変換・日付タイムゾーン・削除ポリシーをカバーする。"
---

# API Design

## 実装前チェック

1. `docs/` の仕様書で要件を確認する
2. Request/Response 型を `app/features/<domain>/<sub>/schemas.py` の Pydantic スキーマで定義する
3. Service 層は Result パターンで返す（HTTP 知識を持たせない）
4. プライバシー要件を `.github/skills/privacy/SKILL.md` で確認する
5. 既存エンドポイントの変更は後方互換性を維持するか、`/v2/` を採用する
6. 破壊的変更は `Deprecation` ヘッダ付与 + ADR に移行手順を記録する

---

## API パス命名規約

> **理由**: 8 名並行開発で API パスの命名がバラつくと、フロントエンド開発者が URL を推測できず、ドキュメント参照コストが増大する。

| ルール                                  | 例                                                                                                    |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| リソース名は **複数形** の `kebab-case` | `/api/v1/products`, `/api/v1/task-templates`                                                          |
| ネストは **2 階層まで**                 | `/api/v1/products/{product_id}/countries`                                                             |
| 3 階層以上はフラット化する              | NG: `/products/{id}/countries/{cid}/applications` → OK: `/applications?product_id=xxx&country_id=yyy` |
| アクション系は動詞を使用                | `/api/v1/shipping-gate/{id}/approve`, `/api/v1/shipping-gate/{id}/reject`                             |
| 一括操作は `/bulk` サフィックス         | `/api/v1/tasks/bulk`                                                                                  |
| バージョンはパスプレフィックス          | `/api/v1/...`, `/api/v2/...`                                                                          |

---

## レイヤー責務（禁止含む）

> **理由**: レイヤーの責務を厳密に分離することで、8 名並行開発でのコンフリクトを最小化し、テスト容易性を確保する。

| レイヤー       | 責務                                                | 禁止                                |
| -------------- | --------------------------------------------------- | ----------------------------------- |
| **Router**     | HTTP 入力検証・Result→HTTP 例外変換・レスポンス整形 | ビジネスロジック・DB アクセス       |
| **Service**    | ビジネスロジック・トランザクション制御・Result 生成 | HTTP 知識（StatusCode 等）・直接 DB |
| **Repository** | DB アクセス・クエリ構築・SQLAlchemy 操作            | ビジネスロジック・HTTP 知識         |

## Router → HTTP 変換

```python
from app.common.result_to_http import to_http_exception

@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    dto: UpdateTaskRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: TasksService = Depends(get_tasks_service),
) -> TaskResponse:
    result = await service.update(task_id, dto, user.scope)
    if not result.ok:
        raise to_http_exception(result.error)
    return TaskResponse.model_validate(result.value)
```

---

## 日付・タイムゾーン

- 保存・通信: UTC ISO 8601（`2026-04-10T12:00:00Z`）
- 表示変換（UTC→ローカル）: フロントエンドのみで実施する
- 直接ログ: UTC。現地時間は使用しない
- `datetime.now()` のサーバー直接使用禁止 → `Clock` ファクトリ経由（L2 ルール）

```python
def __init__(self, clock: Clock):
    self.clock = clock

now = self.clock.now()  # UTC datetime
```

---

## データ削除ポリシー

> **理由**: 論理削除の統一により、監査証跡を維持し、誤操作からの復旧を可能にする。

- 論理削除: `delete_flg: 0`（`deleted_at` は使用しない）
- 物理削除が必要な場合: ADR 作成 + 論理保持期間確定後に人間が承認

---

## セキュリティ考慮

- 全エンドポイントに認証・認可チェックを実装する（`Depends(get_current_user)`）
- エラーレスポンスにスタックトレース・内部クラス名・DB エラー詳細を含めない（L1 ルール）
- 入力は Pydantic スキーマで検証する
- エンドポイント追加・変更時に認可チェックの動作を確認する

```python
# NG: DB エラー内容がクライアントに漏洩
raise HTTPException(status_code=500, detail=str(err))

# OK: 抽象化メッセージ
raise HTTPException(status_code=500, detail="Internal server error")
```

---

## レスポンス型の一貫性

> **理由**: 同じエンティティが画面ごとに違う JSON 構造で返ると、フロントエンドが混乱し、バグの温床になる。

- **1 エンティティ = 1 標準レスポンス型**（`{Entity}Response`）を SSOT とする
- 画面固有の追加情報が必要な場合は **標準型を継承して拡張** する（`TaskDetailResponse(TaskResponse)` 等）
- 標準型からフィールドを **削る方向の派生は原則禁止**（フロントエンドが「あるはず」のフィールドで壊れる）
- 軽量レスポンスが必要な場合は `{Entity}SummaryResponse` を別途定義する（標準型の継承ではなく独立定義）

---

## レビュー自己チェックリスト

`copilot-instructions.md` §L1/L2 を参照してセルフチェックを行う。
