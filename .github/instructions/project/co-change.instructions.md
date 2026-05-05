---
description: "同時変更必須ペア（Co-change）の規約。L1/L2 ペア表を定義し、トリガー側のみの編集完了を禁止する。"
---

# Co-change Standards

> このファイルは `copilot-instructions.md` の L1/L2 ルールの **SSOT**。
> Co-change ペアの追加・変更はこのファイルを更新し、`copilot-instructions.md` の箇条書きと整合させること。

---

## L1 ペア（同時変更必須 — 片側のみで応答完了禁止）

| #   | トリガー（変更対象）                                           | 必ず同時変更するファイル                                | 理由                                                                                      |
| --- | -------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1   | `app/batch/jobs/batch_*.py` 新規作成 / 削除                    | `app/batch/cli.py` の `_JOB_REGISTRY`                   | CLI 経由のバッチ起動登録。未登録のジョブは実行不能                                        |
| 2   | `app/core/auth/permissions.py` への Action 追加                | 対応 router の `permission_required` 適用               | 権限定義だけして Depends を付与しないと未保護エンドポイントが残る（L1: 認可チェック漏れ） |
| 3   | `app/db/models/*.py` / `app/features/*/models.py` のカラム変更 | `alembic/versions/` への新規 revision 追加              | ORM モデルと DB スキーマの乖離 → `42S22` エラー                                           |
| 4   | `app/core/i18n_resources/ja.json` へのキー追加                 | `en.json` / `zh-CN.json` / `vi.json` 3 ファイル同時更新 | 4 ロケール未同期 → 翻訳抜け                                                               |
| 5   | `frontend/src/` 配下の `SCR*_*.tsx` 新規作成                   | `frontend/src/App.tsx` のルーティング登録               | 画面が存在しても URL 未登録 → 404                                                         |
| 6   | `app/features/*/schemas.py` の Response 型変更                 | `frontend/src/api/types.ts` の対応型更新                | フロント型と API レスポンスの乖離 → 実行時エラー                                          |

---

## 確認手順（AI 向け）

1. 変更対象ファイルがL1ペア表の「トリガー」に該当するか確認する
2. 該当する場合は **必ず** ペア先の変更も応答に含める。含めずに完了とすることは L1 違反
3. L2 ペアに該当する場合は `[L2 警告]` を付して、推奨同時変更先をユーザーに案内する

---

## 参照

- `copilot-instructions.md` §L1 / §L2 — ルール優先レベルの定義
- `instructions/project/batch.python.instructions.md` — バッチ実装規約（ペア #1）
- `instructions/project/authorization.python.instructions.md` — 認可実装規約（ペア #2）
- `instructions/project/i18n.instructions.md` — 多言語対応規約（ペア #4）
