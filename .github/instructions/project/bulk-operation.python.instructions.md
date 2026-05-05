---
description: "一括操作の実装規約。AuditLog・BulkUpdateService・テストパターンを定義する。"
applyTo: "**/*.py"
---

# Bulk Operation Standards

## L1 ルール

- 監査対象エンティティの **一括 UPDATE** を AuditLog 書き込みなしで実行禁止
- BulkUpdateService を経由せずに一括更新 API を作成禁止
- `BulkUpdateService.bulk_update()` に **1000 件超** の `items` を渡すこと禁止（API 受付上限）

> **スコープ**: AuditLog は監査証跡（規制業務要件）として必須。
> 単一レコードの新規登録（CREATE）は AuditLog 対象外。

## L2 ルール

- 一括操作のリクエスト件数が **100 件を超える**場合は事前警告（L1 上限 1000 件の手前での早期通知）

## 実装パターン

### BulkUpdateService の使用

```python
result = await bulk_update_service.bulk_update(
    items=[
        BulkUpdateItem(entity_type="Task", entity_id=item.id, data=item.changes)
        for item in items
    ],
    user_id=user_id,
)
```

### トランザクション境界

- **内部 chunking 単位**: 50 件（`BULK_BATCH_SIZE = 50`）— BulkUpdateService 内部のトランザクション分割単位
- **L2 警告ライン**: 100 件（API 受付可能だが処理負荷の事前通知）
- **L1 上限**: 1000 件（API 受付段階で拒否。`BulkUpdateService.bulk_update()` がエラーを返す）

### テスト

テストでは以下のパターンを必須とする:

1. **正常系**: 一括更新が全件反映され、AuditLog が各エンティティ分書き込まれること
2. **部分失敗**: 一部エンティティが存在しない場合のエラーハンドリング
3. **競合**: 他ユーザーによる変更後（`row_version` 不一致）で `ConflictWarning` が返ること
4. **チャンキング境界**: 1000 件超で L1 違反として拒否されること

## 参照
