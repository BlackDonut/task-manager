---
description: "TypeScript（Vitest + @testing-library/react）のテスト規約。AAA 構造・モック戦略・コンポーネント / フック / ユーティリティのテストパターン・PII 禁止をカバーする。"
applyTo: ["**/*.{test,spec}.{ts,tsx}", "**/tests/**/*.{ts,tsx}"]
---

# Test Standards (TypeScript / Vitest)

## 基本ルール

- フレームワーク: **Vitest** + **@testing-library/react**
- テスト環境: `jsdom`（`vitest.config.ts` で設定済み）
- 構造: **Arrange / Act / Assert**
- テスト説明文: 「〜の場合、〜になる」形式
- `console.log` をテスト内に残さない
- 1 テスト = 1 論理アサーション（同じ振る舞いの複数属性確認は許容）

## テストデータ

- **PII 禁止**。ダミー値は英数字（`'user-001'`, `'task-abc'`）

## モック戦略

| テスト対象                    | 戦略                                           |
| ----------------------------- | ---------------------------------------------- |
| 純粋関数 / ユーティリティ     | モックなし                                     |
| API 呼び出し（axios / fetch） | `vi.mock` でモジュール全体をモック             |
| React Query                   | `QueryClient` を wrap してキャッシュをリセット |
| タイマー / 日時               | `vi.useFakeTimers()`                           |
| カスタムフック                | `renderHook` + `vi.fn` で依存を注入            |

## ファイル配置

```
frontend/src/
├── utils/
│   ├── formatDate.ts
│   └── formatDate.test.ts      # ユーティリティと同じ階層に配置
├── hooks/
│   ├── useTaskStatus.ts
│   └── useTaskStatus.test.ts
└── components/
    ├── TaskCard.tsx
    └── TaskCard.test.tsx
```

---

## AAA 構造例

### ユーティリティ関数

```ts
describe("formatDate", () => {
  test("UTC 日付を YYYY-MM-DD 形式に変換する", () => {
    // Arrange
    const input = "2026-04-25T12:00:00Z";

    // Act
    const result = formatDate(input);

    // Assert
    expect(result).toBe("2026-04-25");
  });
});
```

### カスタムフック

```ts
import { renderHook, act } from "@testing-library/react";
import { vi } from "vitest";

describe("useTaskStatus", () => {
  test("ステータス更新後に新しいステータスが返る", async () => {
    // Arrange
    const mockUpdate = vi.fn().mockResolvedValue({ status: "done" });
    const { result } = renderHook(() =>
      useTaskStatus({ onUpdate: mockUpdate }),
    );

    // Act
    await act(async () => {
      await result.current.updateStatus("task-001", "done");
    });

    // Assert
    expect(result.current.status).toBe("done");
  });
});
```

### React コンポーネント

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("TaskCard", () => {
  test("タスク名が表示される", () => {
    // Arrange
    const task = {
      id: "task-001",
      title: "テストタスク",
      status: "not_started",
    };

    // Act
    render(<TaskCard task={task} />);

    // Assert
    expect(screen.getByText("テストタスク")).toBeInTheDocument();
  });

  test("完了ボタンを押すと onComplete が呼ばれる", async () => {
    // Arrange
    const onComplete = vi.fn();
    const task = {
      id: "task-001",
      title: "テストタスク",
      status: "in_progress",
    };
    render(<TaskCard task={task} onComplete={onComplete} />);

    // Act
    await userEvent.click(screen.getByRole("button", { name: "完了" }));

    // Assert
    expect(onComplete).toHaveBeenCalledWith("task-001");
  });
});
```

### API モック（axios）

```ts
import { vi } from "vitest";
import axios from "axios";

vi.mock("axios");
const mockedAxios = vi.mocked(axios);

describe("TaskApi", () => {
  test("タスク一覧を取得する", async () => {
    // Arrange
    mockedAxios.get.mockResolvedValue({
      data: { items: [{ id: "task-001" }] },
    });

    // Act
    const result = await taskApi.list();

    // Assert
    expect(result.items).toHaveLength(1);
  });
});
```

---

## セレクタ戦略（コンポーネントテスト）

優先順位（`@testing-library` の推奨に従う）:

| 優先度 | セレクタ         | 例                                              |
| ------ | ---------------- | ----------------------------------------------- |
| 1      | `getByRole`      | `screen.getByRole('button', { name: '保存' })`  |
| 2      | `getByLabelText` | `screen.getByLabelText('タスク名')`             |
| 3      | `getByText`      | `screen.getByText('テストタスク')`              |
| 4      | `getByTestId`    | `screen.getByTestId('task-row')` — 最終手段のみ |

`data-testid` は意味的な属性で取得できない場合にのみ使用する。

---

## React Query を使うコンポーネントのテスト

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false }, // テスト中はリトライしない
    },
  });
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}
```

---

## 禁止事項

- `waitFor` / `findBy*` の代わりに `setTimeout` で待機する
- `getByTestId` を「まず試す」（意味的セレクタを先に試すこと）
- テストデータに PII（実在する名前・メール・電話番号等）を含める
- テスト間でグローバル状態を共有する（各テストは独立させる）
- `any` 型をテストコードに使用する（型安全なモック: `vi.mocked()` を使う）

---

## テストコードのコメント

```ts
/** タスクカードの表示テスト（SCR004 タスク管理） */
describe("TaskCard", () => {
  test("期限超過の場合は警告スタイルが適用される（業務ルール: 期日超過可視化）", () => {
    // Arrange
    // Act
    // Assert
  });
});
```

- `describe` の JSDoc: 対応する画面 ID または機能要件 ID（`FR-XXX` / `SCR-XXX`）
- `test` / `it` の説明文: テスト対象の業務ルールまたは境界条件を 1 文で
- AAA（Arrange/Act/Assert）セクションコメントを記述する

---

## 参照

- Python 側のテスト規約: [testing.python.instructions.md](testing.python.instructions.md)
- コメント規約: [comment-convention.typescript.instructions.md](comment-convention.typescript.instructions.md)
