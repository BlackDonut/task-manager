---
description: "ソースコードのコメント規約。初心者混在・10年運用・AI駆動開発を前提に、構造ナビゲーション用コメント・構造化TODO・業務ルール根拠の記述ルールを定義する。"
applyTo: ["**/*.py"]
---

# Comment Convention

> **設計根拠**: 8 名並行・初心者混在・10 年運用・AI 駆動開発のプロジェクト特性から、以下を両立する。
>
> - 初心者が迷わず読める **構造ナビゲーション**（クラス・メソッド・フィールド・定数）
> - 10 年後もコメントが腐らない **「なぜ」中心** のインラインコメント
> - CI で機械検出可能な **構造化 TODO**

---

## 1. モジュール docstring（ファイル先頭） — 必須

このファイルが「何を担当し」「どの仕様に対応するか」を明示する。初心者・AI が最初に読む情報。

```python
"""タスク依存関係の Repository.

仕様: docs/04_database/tables/TBL-008-task-dependency.md
画面: SCR004（タスク管理）
業務制約: タスク依存関係は DAG 構造を保証する（循環禁止）
"""
```

### 必須項目

| 項目        | 内容                                     | 省略可否   |
| ----------- | ---------------------------------------- | ---------- |
| 1 行目      | このモジュールの責務（1 文）             | 必須       |
| `仕様:`     | 対応する設計ドキュメントへの相対パス参照 | 必須       |
| `画面:`     | 対応する画面 ID（該当する場合）          | 任意       |
| `業務制約:` | このモジュールが守るべきドメインルール   | 該当時必須 |

---

## 2. クラス docstring — 必須

```python
class TasksService:
    """タスクの業務ロジックを担当する Service."""
```

- 1 文でクラスの責務を記述する
- レイヤー（Service / Repository / Router）を明記する

> **[L2]** Service / Router クラスの **モジュール docstring（§1）** に `仕様:` 参照が欠落している場合は L2 違反（`[L2 警告]`）。
> ファイル先頭の module docstring に `仕様: docs/...` または `仕様ソース: docs/...` を必ず記述すること。
> クラス docstring への `仕様:` 転記は代替にならない（module docstring がなければ AI が読み飛ばす）。

---

## 3. メソッド docstring — 必須

```python
async def update_status(
    self,
    task_id: str,
    new_status: str,
    scope: OrganizationScope,
) -> Result[TaskDto]:
    """タスクのステータスを更新する.

    Args:
        task_id: 対象タスクの ID
        new_status: 遷移先ステータス
        scope: 組織スコープ（認可用）

    Returns:
        更新後の TaskDto、またはエラー
    """
```

### 記述ルール

- 1 行目: メソッドが **何をするか**（1 文）
- `Args:`: 型名から業務上の意味が **自明でない** 場合のみ記述する。型名の繰り返しは禁止
- `Returns:`: 戻り値の業務上の意味（Result パターンの場合は `Ok/Err` の内容を書く）
- private メソッド（`_` プレフィックス）: docstring 任意。ただし業務ルールに関わる場合は必須

```python
# OK: 引数の意味が型名から自明 → 1 行で十分
def list_all(self, scope: OrganizationScope) -> Result[list[TaskResponse]]:
    """組織スコープ内の全タスクを返す。"""

# OK: 意味が自明でない引数は Args: を追加
def update_status(self, task_id: str, new_status: TaskStatus, scope: OrganizationScope) -> Result[TaskResponse]:
    """タスクのステータスを更新する。

    Args:
        task_id: 対象タスクの ID
        new_status: 遷移先ステータス（状態機械で制約）
        scope: 認可用の組織スコープ
    """

# NG: 型名の繰り返し
# Args:
#     task_id: str - タスク ID（str 型）
```

---

## 4. モデル（テーブル定義）のフィールドコメント — 必須

初心者が最も困るのは「このカラムは何？」。DB 設計書への往復コストを削減する。

```python
class Task(Base):
    """タスク（TBL-006）."""

    __tablename__ = "tasks"

    id: Mapped[str]                    # タスク ID（UUID v7）
    title: Mapped[str]                 # タスク名
    status: Mapped[str]                # ステータス（draft/in_progress/completed）
    due_date: Mapped[datetime]         # 期限日（UTC）
    assignee_id: Mapped[str | None]    # 担当者 ID（users.id）
    project_id: Mapped[str]            # 所属プロジェクト ID（projects.id）
    delete_flg: Mapped[int]            # 論理削除フラグ（0: 有効, 1: 削除済み）
```

### 記述ルール

- フィールド名から **業務上の意味が自明でない** 場合のみコメントを追加する（`title`、`name` 等は不要）
- FK の場合は参照先テーブル・カラムを明記する（例: `users.id`）
- 取りうる値が限定的な場合は列挙する（例: `not_started/in_progress/done`）
- 業務ルール・制約がある場合は短く理由を記述する
- クラス docstring に対応するテーブル定義 ID（`TBL-XXX`）を記載する

---

## 5. Pydantic スキーマのフィールド — 必須

API の入出力定義。フロントエンド開発者も読むため、`Field.description` に日本語で意味を書く。

```python
class CreateTaskRequest(BaseModel):
    """タスク作成リクエスト."""

    title: str = Field(..., description="タスク名", max_length=200)
    due_date: datetime = Field(..., description="期限日（UTC）")
    assignee_id: str | None = Field(None, description="担当者 ID")
    project_id: str = Field(..., description="所属プロジェクト ID")
```

### 記述ルール

- `Field(description=...)` を必ず設定する（OpenAPI ドキュメントにも反映される）
- バリデーション制約（`max_length`, `ge`, `le` 等）も `Field` に含める
- クラス docstring に「〜リクエスト」「〜レスポンス」を明記する

---

## 6. 定数・Enum — 必須

値の意味が名前だけでは不明なもの。

```python
class TaskStatus(str, Enum):
    """タスクステータス（状態遷移図: basic-design.md §5）."""

    DRAFT = "draft"              # 下書き（編集可能）
    IN_PROGRESS = "in_progress"  # 進行中（作業中）
    APPROVED = "approved"        # 承認済み（次フェーズ移行可能）
    REJECTED = "rejected"        # 差し戻し（再対応必要）
```

```python
# エスカレーション警告の閾値（FR-011 エスカレーション管理）
ESCALATION_WARNING_DAYS = 7
```

### 記述ルール

- Enum: 各値にインラインコメントで業務上の意味を記述する
- Enum クラス docstring: 対応する設計ドキュメントのセクションを参照する
- 定数: Magic number 禁止。定数名 + コメントで意味と根拠を明示する

---

## 7. インラインコメント（処理の中身） — 「なぜ」のみ

処理ロジック内では **「何をしているか」ではなく「なぜそうしているか」** を書く。

```python
# OK: なぜを説明
# 未承認状態で次フェーズに進める状態遷移を防ぐ（業務ルール: 未承認禁止）
if task.status != TaskStatus.APPROVED:
    return Err(error=AppError(type="BUSINESS_RULE", message="..."))
```

---

## 8. 業務ルール・規制根拠コメント

規制遵守に直結するロジックには `[業務ルール]` プレフィックスを付け、根拠ドキュメントを参照する。

```python
# [業務ルール] 未承認禁止（copilot-instructions.md §業務上の絶対条件 #2）
# タスクステータスが APPROVED 以外の場合、次フェーズに移行させない
async def check_approval_gate(self, task_id: str) -> Result[bool]:
    ...
```

```python
# [業務ルール] 期日超過エスカレーション（FR-011 エスカレーション管理）
# 期日の N 日前に警告、超過時に上長へ自動通知
ESCALATION_WARNING_DAYS = 7
```

---

## 9. 構造化 TODO コメント

> **禁止**: プレフィックスなしの裸の `# TODO` / `# FIXME` / `# HACK` は禁止。
> 理由: 誰が・いつまでに・なぜ残したかが不明になり、10 年運用で死蔵する。

| プレフィックス           | 用途                         | ルールレベル | CI 挙動      | 書式                                                      |
| ------------------------ | ---------------------------- | ------------ | ------------ | --------------------------------------------------------- |
| `# TODO(security):`      | セキュリティ脅威で未レビュー | **L1**       | **ブロック** | `# TODO(security): <脅威> - requires review before merge` |
| `# TODO(domain):`        | 仕様未確定で実装停止         | **L2**       | 警告         | `# TODO(domain): <疑問点> - 要確認`                       |
| `# TODO(impact):`        | 影響範囲未調査で実装停止     | **L2**       | 警告         | `# TODO(impact): <対象> - 要調査`                         |
| `# TODO(perf):`          | 既知のパフォーマンス課題     | L3           | 表示のみ     | `# TODO(perf): <課題と回避策案>`                          |
| `# TODO(<期日> <担当>):` | 期限付き技術的負債           | L3           | 表示のみ     | `# TODO(2026-12-31 yamada): <内容>`                       |

```python
# NG: 裸の TODO
# TODO: あとで直す

# OK: 構造化 TODO
# TODO(2026-06-30 tanaka): バッチサイズ最適化。現在固定 1000 件だが負荷試験後に調整
BATCH_CHUNK_SIZE = 1000
```

---

## 10. `ASSUMPTION:` コメント

AI 生成コード・仕様推測で補完した箇所に付与する。人間レビューのトリガー。

```python
# ASSUMPTION: 申請ステータスの遷移順は draft → submitted → approved のみ。
#             docs/02_basic-design/01_common/basic-design.md に明記なし。要確認。
VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["submitted"],
    "submitted": ["approved"],
}
```

**L1 制約**: セキュリティ・認証・認可・データモデル破壊的変更には `ASSUMPTION:` 使用禁止。仕様確認を人間に求めること。

---

## 11. セクションコメント

長い関数内のブロックを論理的に区切る。ただしセクションが 3 つ以上になる場合は **関数分割を優先** する。

```python
# --- バリデーション ---
...

# --- 状態遷移 ---
...

# --- 監査ログ記録 ---
...
```

---

## 12. 書かないコメント（禁止）

| パターン                                             | 理由                                            |
| ---------------------------------------------------- | ----------------------------------------------- |
| コードの直訳（`# i に 1 を足す`）                    | コードで自明。初心者にも読ませて成長を促す      |
| ローカル変数の逐一説明                               | 変数名で自明にする（命名で解決）                |
| import 文の説明                                      | IDE で定義元に飛べる                            |
| 変更履歴（`# 2026-04-19 yamada: 追加`）              | Git で管理する                                  |
| コメントアウトされたコード                           | 未使用コード追加禁止（copilot-instructions.md） |
| 裸の `# TODO` / `# FIXME` / `# HACK`                 | 構造化プレフィックス必須（§9）                  |
| PII を含むコメント（`# 田中太郎のリクエストで追加`） | プライバシー規約違反                            |

---

## 13. テストコードのコメント

→ テストクラス docstring（`FR-XXX`）・メソッド docstring・AAA セクションコメントの規約は `testing.python.instructions.md` を参照。

---

## 判断フローチャート

```
コードを書いた
  ├─ クラス / メソッド？ → docstring を書く（責務 + Args/Returns）
  ├─ モデル / スキーマのフィールド？ → インラインコメント or Field(description=) を書く
  ├─ 定数 / Enum？ → 意味と根拠を書く
  ├─ 業務ルール / 規制に関わる？ → [業務ルール] + 根拠ドキュメント参照を書く
  ├─ セキュリティ未レビュー？ → # TODO(security): ... を書く
  ├─ 仕様未確定？ → # TODO(domain): ... or ASSUMPTION: を書く
  ├─ なぜこう書いたか非自明？ → 「なぜ」コメントを書く
  ├─ パフォーマンス懸念あり？ → # TODO(perf): ... を書く
  └─ 上記以外？ → コメント不要（命名で解決する）
```
