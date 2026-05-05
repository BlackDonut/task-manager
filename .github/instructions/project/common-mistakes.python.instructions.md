---
description: "よくある間違いとその防止策。Result忘れ・delete_flgフィルタ漏れ・直接DB操作等、ジュニアが犯しやすいパターンを一覧化する。"
applyTo: ["**/*.py"]
---

# よくある間違い（FAQ）

> **DRY 原則**: 各項目の詳細・コード例は原典を参照。ここでは「何が間違いか」の簡潔なリストと参照リンクのみ記載。

---

## Python

### ❌ `Any` を使ってしまう

`object` または具体的な型を使用する。Pydantic で型を生成するのも有効。

→ 詳細・コード例: [python.instructions.md](python.instructions.md)

### ❌ Service 層から raise する

Service 層では `raise` ではなく `Result` パターン（`Err(error=AppError(...))`）でエラーを返す。

→ 詳細・コード例: [python.instructions.md](python.instructions.md)

### ❌ 戻り値型ヒントを省略する

全関数の戻り値型ヒントを明示する。非同期関数は `Result[T]` を返す。

→ 詳細・コード例: [python.instructions.md](python.instructions.md)

---

## FastAPI / バックエンド

### ❌ Router にビジネスロジックを書く

Router は HTTP 入力検証・Result→HTTP 例外変換・レスポンス整形のみ。ビジネスロジック・DB アクセスは Service に委譲。

→ 詳細・コード例: [api-design.instructions.md](api-design.instructions.md)

### ❌ Service の Result を `to_http_exception` を使わずに展開する

Router 層では必ず `to_http_exception()` で Result → HTTP 例外変換を行う。

→ 詳細・コード例: [python.instructions.md](python.instructions.md) — Router 層での Result 展開

### ❌ datetime.now() を直接使う

`Clock` ファクトリ経由で取得する（`self.clock.now()`）。

→ 詳細・コード例: [api-design.instructions.md](api-design.instructions.md) — 日付・タイムゾーン

### ❌ try/except のスコープが DB 取得のみで、変換処理が外に出ている

**実際に発生した不具合（2026-04）**: `list_all` / `list_filtered` 等の Service メソッドで
`rows = repo.list_all(scope)` だけを try/except で囲み、その後の `_to_response()` や
集計関数（`_enrich_with_aggregates()` 等）を try/except の外に書いた結果、
変換中の例外（Enum 変換エラー・NULL 比較 TypeError 等）が FastAPI のデフォルト
エラーハンドラーに到達し **HTTP 500** となった。
フロントエンドは全一覧系 API が 500 を返すため「読み込みに失敗しました」が表示され続けた。

```python
# NG: DB取得だけが try 内で、変換処理が外に出ている
def list_all(self, scope):
    try:
        rows = self._repo.list_all(scope)
    except Exception as exc:
        return Err(AppError(type="INTERNAL", ...))
    # ↓ ここで Enum 変換エラーや None 比較 TypeError が起きると 500 になる
    return Ok(value=[_to_response(r) for r in rows])

# OK: DB取得〜変換処理〜集計まで全て同一の try 内に入れる
def list_all(self, scope):
    try:
        rows = self._repo.list_all(scope)
        return Ok(value=[_to_response(r) for r in rows])
    except Exception as exc:
        self._log.error("list_all.failed", error=str(exc))
        return Err(AppError(type="INTERNAL", ...))
```

**追加の対策**: `_to_response()` 内で Enum 変換する際は DB 値が定義済み Enum 値か
必ず検証する。NULL になりうるカラムを文字列比較する前は `is not None` でガードする。

→ Service 層のエラー処理全般: [python.instructions.md](python.instructions.md)

### ❌ エラーレスポンスに内部情報を含める

DB エラー内容やスタックトレースをクライアントに返さない。`"Internal server error"` 等の抽象メッセージのみ。

→ 詳細・コード例: [api-design.instructions.md](api-design.instructions.md) — セキュリティ考慮

---

## SQLAlchemy / データベース

### ❌ delete_flg フィルタを忘れる

```python
# NG: 論理削除済みレコードも取得してしまう
stmt = select(Task)

# OK: delete_flg == 0 を必ず付ける
stmt = select(Task).where(Task.delete_flg == 0)
```

### ❌ 文字列結合で SQL を組み立てる

```python
# NG: SQL インジェクション
await session.execute(text(f"SELECT * FROM Task WHERE id = '{user_input}'"))

# OK: バインドパラメータ
await session.execute(text("SELECT * FROM Task WHERE id = :id"), {"id": user_input})
```

### ❌ Boolean カラムに `.is_(True)` / `.is_(False)` を使う

**実際に発生した不具合（2026-04）**: SQLAlchemy の `.is_(False)` が SQL Server に対して
`IS 0` を生成し、構文エラーになる。SQL Server は `IS` を NULL 比較専用構文として扱うため、
`IS 0` / `IS 1` は不正。`== False` / `== True` に統一することで `= 0` / `= 1` が生成される。

```python
# NG: SQL Server では IS 0 が生成されて構文エラー
stmt = stmt.where(Notification.is_read.is_(False))

# OK: = 0 が生成されて正常動作（noqa コメントで Ruff E712 を抑制）
stmt = stmt.where(Notification.is_read == False)  # noqa: E712
```

> **影響ファイル**: `Boolean` 型カラムを `.is_(True/False)` で比較している全 Repository。
> SQLite / PostgreSQL では動作するため CI テストで検出されにくい点に注意。

### ❌ ORM モデルにカラムを追加してマイグレーションを作らない

**実際に発生した不具合（2026-04）**: ORM モデルに `application_status` カラムを追加したが
対応する Alembic マイグレーションを作成しなかったため、DB スキーマと乖離し
全申請一覧 API が `42S22: 列名 'application_status' が無効です` で HTTP 500 になった。

- ORM モデルへのカラム追加・削除・変更は必ずマイグレーションファイルとセットで PR に含める
- `scripts/check-er-alembic-models.py` をローカルで実行してスキーマ乖離がないことを確認してからコミットする

```bash
# ローカルでスキーマ乖離チェック
python scripts/check-er-alembic-models.py
```

### ❌ マイグレーションファイルを作ったが `alembic upgrade head` を実行しなかった

**実際に発生した不具合（2026-04）**: `submission_batch_id` カラム追加のマイグレーション
（`i4j5k6l7m8n9`）が `alembic/versions/` に存在していたが、開発環境で `alembic upgrade head`
が実行されず DB スキーマと ORM モデルが乖離した。結果として全申請一覧 API が
`42S22: 列名 'submission_batch_id' が無効です` で HTTP 500 になった。

> 上記の「マイグレーションを作らない」エラーと**症状は同一**だが原因が異なる。
> マイグレーションファイルが存在していても、**未適用なら DB カラムは存在しない**。

- 他メンバーが追加したマイグレーションを取り込んだ後は必ず `alembic upgrade head` を実行する
- サーバー起動前に `alembic current` で最新適用状態を確認する

```bash
# 未適用マイグレーションの確認（head と current が一致しているか確認）
alembic current
alembic heads

# 未適用があれば最新まで適用
alembic upgrade head
```

### ❌ N+1 クエリ

```python
# NG: ループ内で都度クエリ
tasks = (await session.execute(select(Task))).scalars().all()
for task in tasks:
    deps = (await session.execute(
        select(TaskDependency).where(TaskDependency.task_id == task.id)
    )).scalars().all()

# OK: selectinload で一括取得
from sqlalchemy.orm import selectinload
stmt = select(Task).options(selectinload(Task.dependencies))
```

---

## 機能増加で起きやすい間違い

### ❌ 状態遷移チェックを各 feature で独自に if/elif で書く

遷移ルールが散在し、変更時に修正漏れが発生する。`app/common/` の共通遷移チェック関数を使う。

```python
# NG: 各 Service で独自に遷移チェック
if current == "not_started" and new == "in_progress":
    ...
elif current == "in_progress" and new == "done":
    ...

# OK: 遷移テーブル + 共通関数
TASK_TRANSITIONS: dict[str, set[str]] = {
    "not_started": {"in_progress", "cancelled"},
    "in_progress": {"done", "cancelled"},
}
# app/common/ の共通関数で検証
result = validate_transition(TASK_TRANSITIONS, current, new)
```

→ 状態遷移テーブルは Enum 定義の隣に定数として置く（→ `constants-enums.python.instructions.md`）

### ❌ feature から別の feature を直接 import する

循環依存の原因。ID を渡して Router 層で合成するか、`app/common/` に共通 Service を置く。

→ 詳細: [project-structure.instructions.md](project-structure.instructions.md) — feature 間の依存ルール

---

## 非同期（async/await）

### ❌ `await` を付け忘れる

```python
# NG: コルーチンが実行されずオブジェクトが返る（型エラーが出にくいため発見が遅れる）
result = tasks_service.get(task_id)  # awaitなし → Result ではなく coroutine が返る
if not result.ok:  # AttributeError または常に True になる
    ...

# OK
result = await tasks_service.get(task_id)
if not result.ok:
    ...
```

> **注意**: mypy / ruff は `await` 漏れを検出できない場合がある。
> IDE の "coroutine never awaited" 警告を必ず有効にすること。

→ 詳細・理由: [python.instructions.md](python.instructions.md)

### ❌ CPU バウンド処理を async 関数内で直接実行する

```python
# NG: イベントループをブロックし、他の全リクエストが止まる
async def recalculate_dag(tasks: list[Task]) -> Result[dict]:
    result = heavy_cpm_calculation(tasks)  # CPU バウンド処理を直接呼ぶ
    return Ok(value=result)

# OK: run_in_executor でスレッドプールに逃がす
import asyncio
from functools import partial

async def recalculate_dag(tasks: list[Task]) -> Result[dict]:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, heavy_cpm_calculation, tasks)
    return Ok(value=result)
```

> **対象となる処理**: DAG 期日連鎖計算（CPM）、大量データの集計・変換、正規表現による大規模テキスト処理。
> I/O 待ち（DB クエリ・HTTP リクエスト）は該当しない。
