---
description: "TypeScript の定数・Enum 定義規約。as const / 文字列ユニオン型・Magic string 禁止・配置ルール・命名規則・コメント要件を定義する。"
applyTo: ["**/*.{ts,tsx}"]
---

# Constants & Enums Convention (TypeScript)

> **設計根拠**: 8 名並行開発で文字列リテラルの typo が CI で検出不能になることを防ぐ。
> `const enum` は Vite / ESBuild（`isolatedModules: true`）と相性が悪いため、このプロジェクトでは **`as const` オブジェクト** を標準とする。

---

## 1. Enum の実装ルール

### 1.1 `as const` オブジェクトを標準とする

Vite は内部で `isolatedModules: true` でトランスパイルするため、`const enum` は型消去の問題が発生する。
代わりに `as const` オブジェクト + `(typeof X)[keyof typeof X]` の型パターンを標準とする。

```ts
// OK: as const オブジェクト
export const TaskStatus = {
    NOT_STARTED: "not_started", // 未着手
    IN_PROGRESS: "in_progress", // 進行中
    DONE: "done", // 完了
    CANCELLED: "cancelled", // キャンセル（集計から除外）
} as const;

// 型エイリアス（必ず定義する）
export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];
```

```ts
// NG: const enum（Vite + isolatedModules で問題が発生する）
const enum TaskStatus { ... }

// NG: 文字列リテラル直書き
if (task.status === 'in_progress') { ... }
```

### 1.2 文字列ユニオン型（3 値以下の単純なケース）

値が少なく状態遷移もない場合は、`as const` オブジェクトより簡潔な文字列ユニオン型でもよい。

```ts
/** ソート方向 */
export type SortOrder = "asc" | "desc";
```

値が **4 つ以上**、または **業務ステータス**（画面表示・遷移ロジックあり）の場合は `as const` オブジェクトを使用する。

### 1.3 命名規則

| 対象                       | 規則                      | 例                                      |
| -------------------------- | ------------------------- | --------------------------------------- |
| `as const` オブジェクト名  | `PascalCase`              | `TaskStatus`, `ApplicationStatus`       |
| オブジェクトの値（文字列） | `snake_case`（DB と一致） | `'not_started'`, `'in_progress'`        |
| 型エイリアス名             | オブジェクトと同名        | `type TaskStatus = ...`                 |
| スカラー定数               | `UPPER_SNAKE_CASE`        | `MAX_TITLE_LENGTH`, `DEFAULT_PAGE_SIZE` |

### 1.4 コメント要件（`comment-convention.typescript.instructions.md` と連動）

- **オブジェクト直前の JSDoc**: 対応設計ドキュメント参照 ＋ 状態遷移ルール（該当時）
- **各値のインラインコメント**: 日本語で業務上の意味を記述
- スカラー定数: Magic number 禁止。定数名 + コメントで意味と根拠を明示

```ts
/**
 * タスクステータス（状態遷移: docs/02_basic-design/... §5）.
 * 遷移: draft → in_progress → approved / rejected
 */
export const TaskStatus = {
    DRAFT: "draft", // 下書き（編集可能）
    IN_PROGRESS: "in_progress", // 進行中（作業中）
    APPROVED: "approved", // 承認済み（次フェーズ移行可能）
    REJECTED: "rejected", // 差し戻し（再対応必要）
} as const;
export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];
```

---

## 2. スカラー定数の規約

```ts
// エスカレーション警告の閾値（FR-011 エスカレーション管理）
export const ESCALATION_WARNING_DAYS = 7;

// ページネーションのデフォルト取得件数
export const DEFAULT_PAGE_SIZE = 20;

// タスク名の最大文字数（バックエンド TASK_TITLE_MAX_LENGTH と同期すること）
export const TASK_TITLE_MAX_LENGTH = 200;
```

---

## 3. 配置ルール

### 3.1 共有定数・Enum（`src/constants/`）

**2 つ以上のページ・コンポーネントから参照される** 定数・`as const` オブジェクトはここに配置する。

```
src/constants/
├── index.ts          # re-export
├── status.ts         # ステータス系（TaskStatus, ApplicationStatus 等）
├── pagination.ts     # ページネーション定数
└── validation.ts     # 最大文字数等のバリデーション定数
```

### 3.2 ローカル定数（コンポーネント / ページ内）

1 箇所でのみ使用する定数はそのファイルの先頭に定義してよい。
同じ定数を 2 か所目で使う場合は即座に `src/constants/` に移動する（2 回目ルール）。

---

## 4. 値の比較パターン

`as const` オブジェクトを使用した場合、値の比較は定数経由で行う。

```ts
// OK: 定数を使った比較
if (task.status === TaskStatus.IN_PROGRESS) { ... }

// NG: 文字列リテラル直書き（typo を検出できない）
if (task.status === 'in_progress') { ... }
```

---

## 5. 禁止事項

- `const enum` の新規追加（Vite + `isolatedModules` の互換性問題）
- Magic string / Magic number の直書き
- `as const` オブジェクトなしで型ガードを書く（型安全性が失われる）
- バックエンドの Enum 値と異なる文字列を設定する（`// バックエンド XXX と同期すること` コメント必須）
