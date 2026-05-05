---
name: long-term-maintenance
description: "長期保守パターン：依存ライブラリのライフサイクル・破壊的変更の対応・非推奨化戦略・マイグレーションガイド・知識移転。外部ライブラリの追加評価・破壊的変更の計画・5年以上運用するシステムの移行戦略の計画時に使用する。"
applyTo: ["pyproject.toml"]
---

# Long-term Maintenance Skill

5年以上運用するシステムの保守パターン。出力はすべて「提案」。

---

## 依存ライブラリ管理

### ライブラリ追加の原則

全外部ライブラリは ADR に記録。以下の基準で採否を判断:

| 基準             | 確認事項                                          |
| ---------------- | ------------------------------------------------- |
| 必要性           | 標準ライブラリや既存の依存で代替できないか        |
| メンテナンス状況 | 過去 6 ヶ月以内に更新実績があるか                 |
| ライセンス       | 商用利用が許可されているか（MIT / Apache 2.0 等） |
| 依存関係の深さ   | transitive dependencies が少ないか                |
| 既知の脆弱性     | `pip-audit` / `safety check` で脆弱性がないか     |

### バージョン管理

- メジャーバージョンアップは人間が判断
- マイナー/パッチは dependabot で自動更新
- EOL 日を ADR に記録し更新計画を立てる
- `pyproject.toml` でバージョンを固定（`==` または `~=`）

---

## 破壊的変更の扱い

### 変更前に必ずやること

1. ADR 作成（理由・影響範囲・移行方針）
2. 影響クライアント・機能の洗い出し
3. `docs/99_guides/` にマイグレーション手順作成
4. テスト環境で移行検証

### API 後方互換性戦略

Option A: 新旧フィールド並存 + 旧を Deprecated。削除は次 major まで待つ。
Option B: `/v2/resource` + `/v1/resource` に Deprecated ヘッダー。廃止スケジュールを ADR に記録。
禁止: 事前告知なしの破壊的変更

---

## データモデル変更手順

1. ADR 作成 → 2. Alembic マイグレーション作成・テスト → 3. ステージング検証 → 4. レビュー・承認 → 5. ロールバック手順用意

---

## 非推奨化（Deprecation）

1. 告知: `warnings.warn("...", DeprecationWarning)` + ADR 番号
2. 猶予: 最低 1 リリース（目安 3 ヶ月）並存
3. 廃止: ADR に記録して削除

---

## 知識移転

### ドキュメントの鮮度

- コード変更時に `docs/` も同時更新
- 設計判断には ADR 作成
- TODO に期限・担当者明記

### モジュール間依存

`review.instructions.md` の長期保守レビュー観点。Protocol（抽象型）経由で依存し、具象クラスへの直接参照を避ける。

```python
# NG: 具象クラスへの直接依存
from app.db.repositories.sqlalchemy_task_repository import SqlAlchemyTaskRepository

class TaskService:
    def __init__(self, repo: SqlAlchemyTaskRepository) -> None:
        self._repo = repo

# OK: Protocol 経由
from typing import Protocol

class TaskRepository(Protocol):
    async def find_by_id(self, task_id: str) -> Result[Task]: ...
    async def save(self, task: Task) -> Result[None]: ...

class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo
```

### コードの可読性

- Magic number 禁止（定数化）
- ビジネス用語は `docs/` のグロッサリーで管理
- 複雑なロジックに「なぜ」をコメント

### オンボーディング

- 新メンバーは ADR を古い順に読む
- 不明点は `docs/` 確認、なければ Issue に記録

---

## セキュリティ考慮（長期運用時）

長期運用で特に問題になりやすいセキュリティ領域：

| リスク                     | 対策                                                        |
| -------------------------- | ----------------------------------------------------------- |
| 依存ライブラリの脆弱性蓄積 | `pip-audit` を CI で必須とし、高 Severity は即時対応        |
| 認可ロジックの陳腐化       | 機能追加時に必ず認可チェックが機能しているか確認する        |
| ログへの PII 混入増加      | ログ出力コードを変更したら Privacy Skill の規約を再確認する |
| 古い API の認証バイパス    | Deprecated エンドポイントも廃止まで認証・認可を維持する     |

> セキュリティに影響する変更は必ず `# TODO(security): requires review before check-in` を付けること。

---

## エラーハンドリング

- `except` 内で構造化ログを出力
- 外部に返すエラーに内部構造を含めない
- 境界条件を保守サイクルごとに見直す
- `# TODO(domain): エラーケース未検証` で未検証パスを明示
