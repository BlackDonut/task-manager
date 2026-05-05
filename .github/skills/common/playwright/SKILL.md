---
name: playwright
description: "PlaywrightによるE2Eテストの実装パターン：Page Object Model・フィクスチャ・セレクタ戦略・CI設定・デバッグ手法をカバー。E2Eテストの新規作成・Playwrightのレビュー・テスト構造の設計時に使用する。"
applyTo: "tests/e2e/**/*.py"
---

# Playwright Skill

基本ルールは `e2e.python.instructions.md` を参照。

---

## ディレクトリ構造

```
tests/e2e/
├── conftest.py              # Playwright フィクスチャ
├── pages/                   # Page Object Model
│   ├── base_page.py
│   ├── task_list_page.py
│   ├── task_create_page.py
│   └── login_page.py
└── tests/
    ├── test_task_create.py
    ├── test_task_edit.py
    └── test_login.py
```

---

## pytest 設定

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "e2e: E2E tests (Playwright)",
]

# pytest.ini or conftest.py
# pytest-playwright は自動的に page フィクスチャを提供
```

---

## Page Object Model

各画面のインタラクションは Page Object に集約。テストに `page.locator` を直書きしない。

```python
# tests/e2e/pages/task_create_page.py
from playwright.sync_api import Page, Locator


class TaskCreatePage:
    """タスク作成画面の Page Object."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.title_input: Locator = page.get_by_test_id("task-title-input")
        self.submit_button: Locator = page.get_by_test_id("task-create-submit")
        self.error_message: Locator = page.get_by_test_id("form-error-message")

    def fill_title(self, title: str) -> None:
        self.title_input.fill(title)

    def submit(self) -> None:
        self.submit_button.click()

    def get_error_message(self) -> str:
        return self.error_message.inner_text()
```

---

## conftest.py フィクスチャ

```python
# tests/e2e/conftest.py
import pytest
from playwright.sync_api import Page

from tests.e2e.pages.task_list_page import TaskListPage
from tests.e2e.pages.task_create_page import TaskCreatePage


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """認証済みページを返すフィクスチャ."""
    page.goto("/login")
    page.get_by_label("メールアドレス").fill("test-user@example.com")
    page.get_by_label("パスワード").fill("test-password")
    page.get_by_role("button", name="ログイン").click()
    page.wait_for_url("**/dashboard")
    return page


@pytest.fixture
def task_list_page(page: Page) -> TaskListPage:
    return TaskListPage(page)


@pytest.fixture
def task_create_page(page: Page) -> TaskCreatePage:
    return TaskCreatePage(page)
```

---

## テスト実装

```python
# tests/e2e/tests/test_task_create.py
import pytest
from playwright.sync_api import expect

from tests.e2e.pages.task_list_page import TaskListPage
from tests.e2e.pages.task_create_page import TaskCreatePage


@pytest.mark.e2e
def test_create_task_adds_to_list(
    task_list_page: TaskListPage,
    task_create_page: TaskCreatePage,
) -> None:
    """必須項目を入力した場合、タスクが一覧に追加される."""
    # Arrange
    task_list_page.goto()

    # Act
    task_list_page.click_create_button()
    task_create_page.fill_title("task-e2e-001")
    task_create_page.submit()

    # Assert
    expect(task_list_page.get_task_rows()).to_have_count(1)
```

---

## アサーション

Playwright の `expect` は自動リトライ付き。

```python
from playwright.sync_api import expect

# OK: 自動リトライあり（推奨）
expect(page.get_by_test_id("success-toast")).to_be_visible()
expect(page.get_by_test_id("task-row")).to_have_count(3)
expect(page.get_by_test_id("task-title")).to_have_text("task-e2e-001")

# NG: 即時評価のためフレーキーになりやすい
count = page.get_by_test_id("task-row").count()
assert count == 3
```

---

## data-testid の付与ルール

E2E から参照する要素に `data-testid` を付与。命名: `<コンポーネント名>-<役割>`（ケバブケース）。

---

## CI 実行

```yaml
- name: Install Playwright browsers
  run: python -m playwright install --with-deps chromium

- name: Run E2E tests
  run: pytest tests/e2e/ -m e2e -v
  env:
      E2E_BASE_URL: http://localhost:8000
```

---

## デバッグ

```bash
# ヘッド付きで実行
pytest tests/e2e/ --headed

# 特定テストのみ実行
pytest tests/e2e/tests/test_task_create.py -v

# Playwright コードジェネレーターで操作を記録
python -m playwright codegen http://localhost:8000

# トレースビューアーで失敗を調査
python -m playwright show-trace test-results/trace.zip
```
