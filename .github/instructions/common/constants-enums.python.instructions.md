---
description: "定数・Enumの定義規約。StrEnum標準・Magic string禁止・配置ルール・命名規則・コメント要件を定義する。"
applyTo: ["**/*.py"]
---

# Constants & Enums Convention

> **設計根拠**: 8 名並行開発で文字列リテラルの typo が頻発し CI で検出不能になることを防ぐ。
> 初心者が値の業務上の意味を即座に判断できるよう、全 Enum メンバーにコメントを付与する。

---

## 1. Enum 実装ルール

### 1.1 `StrEnum` を標準とする

DB カラムが `NVARCHAR` のため、`StrEnum` を使用する。`IntEnum` は原則禁止（明示的理由がある場合のみ許可）。

```python
from enum import StrEnum

class TaskStatus(StrEnum):
    """タスクステータス（TBL-006）.

    状態遷移: not_started → in_progress → done
              any → cancelled（申請要否変更時に自動設定）
    """

    NOT_STARTED = "not_started"    # 未着手
    IN_PROGRESS = "in_progress"    # 進行中
    DONE = "done"                  # 完了
    CANCELLED = "cancelled"        # キャンセル（進捗・遅延計算から除外）
```

### 1.2 命名規則

| 対象             | 規則                | 例                                         |
| ---------------- | ------------------- | ------------------------------------------ |
| Enum クラス名    | `PascalCase`        | `TaskStatus`, `DependencyType`             |
| Enum メンバー名  | `UPPER_SNAKE_CASE`  | `NOT_STARTED`, `IN_PROGRESS`               |
| Enum `.value`    | DB 格納値と完全一致 | `"not_started"`, `"FS"`                    |
| 定数（スカラー） | `UPPER_SNAKE_CASE`  | `MAX_PAGE_SIZE`, `ESCALATION_WARNING_DAYS` |

### 1.3 コメント要件（`comment-convention.python.instructions.md` と連動）

- **クラス docstring**: 対応テーブル定義 ID（`TBL-XXX`）＋ 状態遷移ルール（該当時）を記載
- **各メンバー**: インラインコメントで日本語の業務上の意味を記述
- **日本語値**: DB 設計に日本語値がある場合はそのまま `.value` に設定する（例: `REQUEST = "依頼"`）

---

## 2. 配置ルール

### 2.1 共有 Enum（`app/core/enums/`）

**2 つ以上のドメイン（features フォルダ）から参照される** Enum はここに配置する。

```
app/core/enums/
├── __init__.py          # re-export
└── <category>.py        # ドメインカテゴリ単位でファイルを分割
```

### 2.2 機能固有 Enum（`app/features/<domain>/crud/enums.py`）

**単一の features フォルダ内でのみ使用される** Enum は機能フォルダに配置する。

```
app/features/<domain>/crud/enums.py   # そのドメイン固有の Enum
```

### 2.3 判断基準

```
この Enum を使うのは 1 機能だけ？
  ├─ Yes → app/features/<domain>/crud/enums.py
  └─ No（2 機能以上）→ app/core/enums/<カテゴリ>.py
```

後から参照元が増えた場合は `core/enums/` に移動する。移動時は既存の import を全て書き換えること。

### 2.4 スカラー定数（`app/core/constants/`）

```
app/core/constants/
├── __init__.py
├── permissions.py       # Actions, Resources（既存設計: common-functions.md §2.5）
├── pagination.py        # MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE 等
└── business.py          # 業務ルール由来の閾値
```

---

## 3. スカラー定数の書き方

```python
# app/core/constants/business.py
"""業務ルール由来の定数.

仕様: docs/02_basic-design/02_feature/FR-011-escalation-management.md
"""

# [業務ルール] エスカレーション警告の閾値（FR-011）
# 期限の N 日前に警告通知を送信する
ESCALATION_WARNING_DAYS = 7

# [業務ルール] 一括操作の最大件数（bulk-operation.python.instructions.md）
# これを超える場合は chunking 必須
BULK_OPERATION_MAX_ITEMS = 1000
```

### ルール

- 1 定数 = 1 コメント行（何の値か ＋ なぜその値か）
- 業務ルール由来は `[業務ルール]` プレフィックス ＋ 根拠ドキュメント参照
- 定数ファイルには **値の定義のみ** 記述する。関数・ロジックは別ファイルに配置

---

## 4. 使用時のルール

### 4.1 文字列リテラル直書き禁止

```python
# NG: typo しても CI で検出不能
if task.status == "done":
    ...

# OK: Enum メンバーを参照
if task.status == TaskStatus.DONE:
    ...
```

### 4.2 数値リテラル直書き禁止

```python
# NG: Magic number
if len(items) > 1000:
    ...

# OK: 名前付き定数
from app.core.constants.business import BULK_OPERATION_MAX_ITEMS

if len(items) > BULK_OPERATION_MAX_ITEMS:
    ...
```

> import は絶対パス必須（→ `python.instructions.md` §絶対 import）

---

## 5. 禁止事項

| パターン                           | 理由                                                |
| ---------------------------------- | --------------------------------------------------- |
| 文字列リテラルでのステータス比較   | typo を CI で検出不能                               |
| `IntEnum` の使用（明示的理由なし） | DB が `NVARCHAR` のため `StrEnum` が標準            |
| 同一 Enum の重複定義               | `core/enums/` の SSOT を import する                |
| Enum メンバーにコメントなし        | 初心者が値の業務上の意味を判断できない              |
| 定数ファイルにロジック記述         | 値の定義のみ。関数は別ファイル                      |
| Enum `.value` と DB 格納値の不一致 | シリアライズ/デシリアライズで変換ロジックが発生する |
