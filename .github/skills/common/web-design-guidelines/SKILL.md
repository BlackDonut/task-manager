---
name: web-design-guidelines
description: "UI コードを Web Interface Guidelines に照らしてレビューする。アクセシビリティ・フォーカス状態・フォーム・アニメーション・タイポグラフィ・パフォーマンス・ダークモード・i18n など 100+ ルールをカバー。「UIをレビューして」「アクセシビリティを確認して」「デザインを監査して」「UXをチェックして」などのタスクで使用する。"
applyTo: "frontend/src/**/*.{tsx,ts,css}"
---

# Web Interface Guidelines

## 使用手順

1. 下記 URL から最新ルールを取得（WebFetch 使用）
2. 指定ファイルを読み込む（未指定時はユーザーに確認）
3. 全ルールに照らしてチェック
4. `file:line` 形式で簡潔に出力

## ガイドラインソース

レビュー前に最新版を取得：

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

取得したコンテンツにすべてのルールと出力フォーマット指示が含まれている。

## 出力フォーマット

ファイル単位でグループ化。`file:line` 形式で簡潔に記載。

```text
## app/components/button.py

app/components/button.py:42 - icon button missing aria-label
app/components/button.py:18 - input lacks label
app/components/button.py:55 - animation missing prefers-reduced-motion

## app/components/modal.py

app/components/modal.py:12 - missing overscroll-behavior: contain

## app/components/card.py

✓ pass
```

問題と場所を明記。修正方法が自明でない場合のみ説明を追加。前置き不要。
