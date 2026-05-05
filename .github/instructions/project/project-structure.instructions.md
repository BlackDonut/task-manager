---
description: "プロジェクトのディレクトリ構造・モジュール命名・ファイル配置ルール。60画面以上を8人で並行開発するための構造規約を定義する。"
---

# Project Structure

## ディレクトリ構造

## 命名規則

| 対象            | 規則        | 例                     |
| --------------- | ----------- | ---------------------- |
| ファイル名      | snake_case  | `task_service.py`      |
| ディレクトリ名  | snake_case  | `features/tasks/`      |
| クラス名        | PascalCase  | `TaskService`          |
| 関数名          | snake_case  | `create_task`          |
| 定数            | UPPER_SNAKE | `MAX_BULK_SIZE = 1000` |
| Pydantic モデル | PascalCase  | `CreateTaskRequest`    |
| 環境変数        | UPPER_SNAKE | `DATABASE_URL`         |

## ドメイングループ定義

### ネストルール

- **すべてのサブ機能をサブディレクトリ化する**（例外なし）
- 単一画面のドメインでも `dashboard/overview/` のようにサブディレクトリを作る
- サブ機能名は画面・機能の責務を表す snake_case 名称（`crud/`, `necessity/`, `gate/` 等）
- 新しいドメイングループの追加は ADR を起こしてチーム合意を得ること

---

## `core/` vs `common/` の境界

> **理由**: 「共通」が曖昧だと、2 つの共通ディレクトリの使い分けが属人化する。以下の基準で機械的に判断する。

| 層            | 配置先        | 責務                                                                                                          | 依存の方向                                                 |
| ------------- | ------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **`core/`**   | `app/core/`   | **インフラ基盤** — DI・DB セッション・Clock・Result 型・Base クラス・ミドルウェア・認証 Depends・型定義・定数 | `features/` → `core/` のみ。`core/` → `features/` 禁止     |
| **`common/`** | `app/common/` | **ビジネス共通** — 2 機能以上で共有するユーティリティ・変換関数・監査ログ・ページネーション・一括更新         | `features/` → `common/` のみ。`common/` → `features/` 禁止 |

**判断基準**:

- DB セッション・認証・設定・型定義・基底クラス → `core/`
- 2 機能以上で使うビジネスロジック補助 → `common/`
- 1 機能でしか使わないもの → その機能のサブディレクトリ内

---

## ファイル配置ルール

1. **1 ファイル 1 責務**（L2 ルール）: Service / Repository / Router を同一ファイルに混在させない。理由: 8 名並行開発での競合を最小化し、変更影響範囲を明確にする
2. **ドメイングループ → サブ機能**: `app/features/<domain>/<sub>/` に router / service / schemas をまとめる
3. **モデル・Repository は機能と同居**: 各サブ機能内に `models.py` / `repository.py` を配置する（`backend-design.md` §3 準拠）。複数サブ機能から参照されるモデルは `<domain>/crud/models.py` に置く
4. **共通処理**: `app/common/` に配置。2 機能以上で使う場合のみ共通化。追加・変更時は `common-functions.md` を先に更新する
5. **テスト**: `tests/` 配下にドメイングループ → サブ機能のミラー構造で配置

## モジュール登録

```python
# app/main.py — ドメイングループ → サブ機能のインポートパターン
from fastapi import FastAPI
from app.features.<domain>.<sub>.router import router as <domain>_<sub>_router

app = FastAPI()
app.include_router(<domain>_<sub>_router, prefix="/api/v1/<domain>", tags=["<domain>"])
```

## feature 間の依存ルール

> **理由**: 60 画面に拡大すると feature 間の相互参照が爆発し、1 テーブル変更で全画面が壊れる。依存方向を一方通行に制限する。

### 依存方向（L2 ルール）

```
features/A → features/B   ❌ 禁止（直接 import しない）
features/* → common/       ✅
features/* → core/         ✅
common/    → core/         ✅
common/    → features/*    ❌ 禁止
core/      → features/*    ❌ 禁止
core/      → common/       ❌ 禁止
```

- feature 間でデータが必要な場合は **ID を渡して Router 層で合成** するか、**`app/common/` に共通 Service を置く**
- `from app.features.tasks.crud.service import TaskService` を `applications/` の Service から呼ぶのは禁止

### 集約画面（ダッシュボード等）のデータ取得

- 全テーブルを 1 SQL で JOIN しない。各ドメインの Service を呼び出し **Router 層でメモリ上合成** する
- 読み取り専用のクロスドメインクエリが不可避な場合は `app/common/queries/` に隔離し、依存テーブルをコメントで明記する

---

## インポートルール

- **絶対インポート**を使用する（相対インポート禁止 — L2 ルール）
- `from app.features.tasks.crud.service import TaskService` ✅
- `from app.features.applications.documents.service import DocumentService` ✅
- `from ..service import TaskService` ❌
- `from app.core.result import Ok, Err, Result` ✅
- `from app.common.soft_delete import not_deleted` ✅
