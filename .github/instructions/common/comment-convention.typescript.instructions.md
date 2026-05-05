---
description: "TypeScript 用のソースコードコメント規約。TSDoc/JSDoc を基本とし、構造化 TODO、業務ルール注記、テストコメント規約を定義します。"
applyTo: ["**/*.{ts,tsx}"]
---

# Comment Convention (TypeScript)

> **設計根拠**: 複数言語・複数担当が混在する大規模コードベースのため、TypeScript 側では `TSDoc/JSDoc` を標準とし、初心者や自動生成ツールが読みやすい注釈を必須化します。

---

## 1. モジュール docblock（ファイル先頭） — 必須

ファイル先頭にそのファイルの責務を 1 文で書き、対応設計書・画面 ID・業務制約を明示してください。TSDoc 形式の docblock を用います。

```ts
/**
 * タスク関連のユーティリティと DTO 定義.
 * 仕様: docs/04_database/tables/TBL-006-tasks.md
 * 画面: SCR004（タスク管理）
 * 業務制約: タスクの期限は UTC で扱う
 */
```

### 必須項目

- 1 行目: モジュールの責務（1 文）
- `仕様:` 対応する設計ドキュメントへの相対パス参照
- `画面:` 対応する画面 ID（該当する場合）
- `業務制約:` ドメインルール（該当時必須）

---

## 2. クラス / インターフェース docblock — 必須

クラス・インターフェースの先頭に 1 行で責務を記述。レイヤー（Service / Repository / Router / UI）を明記してください。

```ts
/**
 * タスクの業務ロジックを提供する Service.
 * Layer: Service
 */
export class TasksService {
    /* ... */
}
```

---

## 3. 関数 / メソッド TSDoc — 必須

1 行目で何をするかを書きます。`@param` / `@returns` は型名から業務上の意味が **自明でない場合のみ** 記述します。型名の繰り返しは禁止。

```ts
// OK: 引数の意味が型名から自明 → 1 行のみ
/**
 * 組織スコープ内の全タスクを返す.
 */
async listAll(scope: OrganizationScope): Promise<TaskDto[]> { /* ... */ }

// OK: 意味が自明でない引数は @param を追加
/**
 * タスクのステータスを更新する.
 *
 * @param taskId 対象タスクの ID
 * @param newStatus 遷移先ステータス（状態機械で制約）
 * @returns 更新後の TaskDTO またはエラー
 */
async updateStatus(taskId: string, newStatus: TaskStatus): Promise<TaskDto> { /* ... */ }
```

---

## 4. DTO / 型のフィールドコメント — 必須

フロント開発者や API ドキュメント生成のため、インターフェース／型のフィールドには **名前から自明でない場合のみ** 短い日本語説明を付けます。FK・Enum・業務ルールありのフィールドは必ず記述します。

```ts
/** タスク作成リクエスト */
export interface CreateTaskRequest {
    /** タスク名（最大200文字） */
    title: string;
    /** 期限日（UTC、ISO 8601 文字列） */
    dueDate: string;
    /** 担当者 ID（users.id） */
    assigneeId?: string | null;
    /** 所属プロジェクト ID（projects.id） */
    projectId: string;
    description?: string; // ← 名前から自明なのでコメント不要
}
```

### 記述ルール

- FK・Enum・業務ルールありのフィールドは必ずコメントを付ける
- `title`、`name`、`description` 等、名前から自明なフィールドは不要
- バリデーション制約（max length、範囲等）はコメントで明示
- FK の場合は参照先テーブル・カラムを記載する

---

## 5. Enum / 定数 — 必須

列挙値や定数は業務上の意味が分かるように各値にコメントを付けます。

```ts
/** タスクステータス（状態遷移図: docs/... §5） */
export const enum TaskStatus {
    /** 下書き（編集可能） */
    DRAFT = "draft",
    /** 進行中（作業中） */
    IN_PROGRESS = "in_progress",
    /** 承認済み（次フェーズ移行可能） */
    APPROVED = "approved",
}

// エスカレーション警告の閾値（FR-011）
export const ESCALATION_WARNING_DAYS = 7; // 日数（業務ルール: FR-011）
```

---

## 6. インラインコメント（処理の中身） — 「なぜ」のみ

処理内コメントでは「何をしているか」ではなく「なぜそれが必要か」を書きます。

```ts
// OK: なぜこの分岐で弾く必要があるかを説明
// [業務ルール] 未承認禁止（copilot-instructions.md §業務上の絶対条件 #2）
if (task.status !== TaskStatus.APPROVED) {
    throw new BusinessRuleError("承認未完了");
}
```

---

## 7. 業務ルール・規制根拠コメント

規制遵守に直結するロジックには `// [業務ルール]` プレフィックスを付け、根拠ドキュメントを明示してください。

```ts
// [業務ルール] 未承認禁止（docs/02_basic-design/... 参照）
function checkApprovalGate(task: Task) {
    /* ... */
}
```

---

## 8. 構造化 TODO コメント

裸の `// TODO` は禁止します。必ずプレフィックス付きで残す人・期限・理由を明記してください。

| プレフィックス              | 用途                         | ルールレベル | CI 挙動      | 書式                                                       |
| --------------------------- | ---------------------------- | ------------ | ------------ | ---------------------------------------------------------- |
| `// TODO(security):`        | セキュリティ脅威で未レビュー | **L1**       | **ブロック** | `// TODO(security): <脅威> - requires review before merge` |
| `// TODO(domain):`          | 仕様未確定で実装停止         | **L2**       | 警告         | `// TODO(domain): <疑問点> - 要確認`                       |
| `// TODO(impact):`          | 影響範囲未調査               | **L2**       | 警告         | `// TODO(impact): <対象> - 要調査`                         |
| `// TODO(perf):`            | 既知のパフォーマンス課題     | L3           | 表示のみ     | `// TODO(perf): <課題と回避策案>`                          |
| `// TODO(YYYY-MM-DD name):` | 期限付き技術的負債           | L3           | 表示のみ     | `// TODO(2026-12-31 yamada): <内容>`                       |

```ts
// NG: 裸の TODO
// TODO: fix later

// OK: 構造化 TODO
// TODO(2026-06-30 tanaka): バッチサイズ最適化。負荷試験後に調整
const BATCH_CHUNK_SIZE = 1000;
```

---

## 9. `ASSUMPTION:` コメント

AI 生成や仕様を推測して補完した箇所には `// ASSUMPTION:` を付けてレビューを促してください。

```ts
// ASSUMPTION: 申請ステータスの遷移順は draft → submitted → approved のみ。docs に明記なし。要確認。
const VALID_TRANSITIONS: Record<string, string[]> = {
    /* ... */
};
```

**L1 制約**: セキュリティ・認可・データモデル破壊的変更には `ASSUMPTION:` 使用禁止。人間に確認を求めてください。

---

## 10. セクションコメント

長い関数のブロック分割は `// ---` を使って論理的に区切ります。ただし 3 つ以上のセクションになる場合は関数分割を優先してください。

```ts
// --- バリデーション ---
...
// --- 状態遷移 ---
...
// --- 監査ログ ---
...
```

---

## 11. 書かないコメント（禁止）

- コードの直訳（`// i に 1 を足す` 等）
- ローカル変数の逐一説明
- import 文の説明
- 変更履歴（Git を使う）
- コメントアウトされたコードを残さない
- 裸の `// TODO` / `// FIXME` / `// HACK` は禁止
- PII を含むコメント（例: `// 田中太郎のリクエスト`）

---

## 12. テストコードのコメント

Jest / Playwright 等のテストでは、テストスイートの docblock に要件 ID（`FR-XXX`）を記載し、各テストは AAA スタイルで `// Arrange` / `// Act` / `// Assert` を付けます。

```ts
/** 承認ゲートテスト（FR-010） */
describe("ApprovalGate", () => {
    test("reject when not approved", async () => {
        // Arrange
        // Act
        // Assert
    });
});
```

---

## 13. 判断フローチャート

```
コードを書いた
  ├─ クラス/インターフェース? → docblock を書く（責務 + 仕様参照）
  ├─ 関数/メソッド? → TSDoc を書く（何をするか。@param は意味が自明でない場合のみ）
  ├─ DTO/型のフィールド? → FK・Enum・業務ルールありなら行コメント。名前で自明なら不要
  ├─ Enum/定数? → 各値に業務意味をコメント
  ├─ 業務ルールに関わる? → // [業務ルール] + 根拠参照を書く
  ├─ セキュリティ未レビュー? → // TODO(security): を書く
  ├─ 仕様未確定? → // TODO(domain): または ASSUMPTION: を付ける
  ├─ 非自明な設計判断? → // ASSUMPTION: を付けて人間レビューを要求
  └─ 上記以外? → コメント不要（命名で解決）
```

---

## コメント粒度の基本方針（まとめ）

| 場所                               | 粒度                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------- |
| モジュール docblock                | 1 行責務 + `仕様:` + 業務制約（該当時）                                    |
| クラス / インターフェース docblock | 1 行（レイヤー名 + 責務）                                                  |
| 関数 / メソッド TSDoc              | 1 行「何をするか」。引数の意味が型名から自明でない場合のみ `@param` を追加 |
| DTO / 型のフィールド               | FK・Enum・業務ルールありのみ。名前で自明なものはコメント不要               |
| Enum 値                            | 全値に短い日本語コメント                                                   |
| インライン処理コメント             | 「なぜ」が必要な場合のみ（コードの直訳は禁止）                             |

---

## 補足

- このファイルは TypeScript に特化したガイドラインです。リポジトリ全体で言語別の注記方針が必要な場合は、さらに言語ごとの `*.instructions.md` を用意してください。
- セキュリティ・認可・PII に関するルールはレポジトリ共通の L1 制約を優先してください（copilot-instructions.md の L1 参照）。
