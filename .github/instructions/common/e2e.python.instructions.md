---
description: "PlaywrightによるE2Eテストの規約。ファイル配置・Page Object Model・セレクタ戦略・pytestとの使い分けをカバーする。"
applyTo: "**/e2e/**/*.py"
---

# E2E Testing (Playwright + pytest)

## 使い分け

| テスト種別     | ツール            | 対象                   |
| -------------- | ----------------- | ---------------------- |
| ユニットテスト | pytest            | Service / Repository   |
| 統合テスト     | pytest + httpx    | Router（API レベル）   |
| E2E テスト     | pytest-playwright | ブラウザ操作・画面遷移 |

## ファイル配置

```
tests/e2e/
├── conftest.py          # Playwright フィクスチャ
├── pages/               # Page Object
│   ├── base_page.py
│   ├── login_page.py
│   └── task_list_page.py
└── tests/
    ├── test_login.py
    └── test_task_crud.py
```

## Page Object Model

→ 実装パターン・コード例は [`skills/playwright/SKILL.md`](../skills/playwright/SKILL.md) を参照。

## セレクタ戦略

| 優先度 | セレクタ                   | 例                                        |
| ------ | -------------------------- | ----------------------------------------- |
| 1      | `get_by_role`              | `page.get_by_role("button", name="保存")` |
| 2      | `get_by_label`             | `page.get_by_label("タスク名")`           |
| 3      | `get_by_test_id`           | `page.get_by_test_id("task-row")`         |
| 4      | `locator("[data-testid]")` | 最終手段のみ                              |

## テスト実装

→ 実装パターン・コード例は [`skills/playwright/SKILL.md`](../skills/playwright/SKILL.md) を参照。

## conftest.py

→ フィクスチャ・認証済みページの実装例は [`skills/playwright/SKILL.md`](../skills/playwright/SKILL.md) を参照。

## 禁止事項

- E2E テストに PII（実在のメール・電話番号等）を含めない
- `page.wait_for_timeout()` の代わりに `page.wait_for_selector()` / `page.wait_for_url()` を使用
- テスト間で状態を共有しない（各テストは独立）。具体的には: DB のテストデータは各テスト関数内またはフィクスチャで作成し、ブラウザの Cookie・localStorage・セッションはテスト間で引き継がない
