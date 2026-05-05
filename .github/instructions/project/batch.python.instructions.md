---
description: "バッチ処理の実装規約。べき等性・OperationId・タイムアウト・構造化ログ・エラーハンドリングを強制する。"
applyTo: "{**/*_batch.py,**/batch/**/*.py}"
---

# Batch Processing Standards

## L1 ルール

- べき等性を保証しないバッチ処理禁止
- バッチで監査対象エンティティを AuditLog 書き込みなしに UPDATE 禁止（→ `bulk-operation.python.instructions.md`）
- バッチの開始・終了・エラーを構造化ログに記録しないことを禁止

## L2 ルール

- リトライなしでバッチ実装時は警告
- 処理件数 1000 件超でチャンク分割なしは警告
- タイムアウト設定省略時は警告

## 実装パターン

### ディレクトリ配置

```
app/batch/
├── __init__.py
├── batch_runner.py            # 共通基盤（ログ・べき等チェック）
├── types.py                   # BatchResult 等の共通型
└── jobs/
    ├── __init__.py
    ├── <job_name>.py              # 各バッチジョブ
    └── tests/
        └── test_<job_name>.py
```

### バッチ基本構造

```python
# app/batch/jobs/<job_name>.py
from app.batch.batch_runner import BatchRunner
from app.batch.types import BatchResult
from app.core.clock import Clock

class <JobName>Job:
    def __init__(self, runner: BatchRunner, repository: <SomeRepository>, clock: Clock):
        self.runner = runner
        self.repository = repository
        self.clock = clock

    async def run(self) -> None:
        await self.runner.execute("<job-name>", self._process)

    async def _process(self) -> BatchResult:
        items = await self.repository.find_target_items(self.clock.now())
        # 各アイテムを処理...
        return BatchResult(processed_count=len(items), failed_count=0)
```

### べき等性の実装パターン

```python
async def process_one(self, task: Task) -> None:
    if task.notified_at is not None:
        return  # 実行済みならスキップ
    await self.notify(task)
    await self.repo.mark_notified(task.id)
```

## テスト

必須パターン:

1. **正常系**: バッチが正しく処理される
2. **べき等性**: 2回実行しても2重処理されない
3. **チャンク境界**: チャンクサイズちょうど/超過時に分割される
4. **エラー時**: 1件失敗しても他の処理が継続する

## 参照

- 一括操作との連携: `bulk-operation.python.instructions.md`
- 監視: `.github/skills/common/monitoring/SKILL.md`
