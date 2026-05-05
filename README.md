# タスク・進捗管理システム

プロジェクト・タスク・担当者を横断して進捗・遅延を可視化し、業務の効率化を支援するシステム。

## 概要

| レイヤー         | 技術                         |
| ---------------- | ---------------------------- |
| バックエンド     | Python 3.12+ / FastAPI       |
| フロントエンド   | React 19 / TypeScript / MUI  |
| データベース     | SQL Server                   |
| バリデーション   | Pydantic v2                  |
| 型チェック       | mypy (--strict)              |
| リンター         | Ruff                         |
| テスト           | pytest + pytest-asyncio      |
| ログ             | structlog                    |

**設計方針**: API ファースト / 3 レイヤーアーキテクチャ（Router → Service → Repository）

## 最初の3ステップ

1. `CONTRIBUTING.md` を読んで、開発フローと禁止事項を把握する。
2. `.github/copilot-instructions.md` を読んで、GitHub Copilot のルールを把握する。
3. `.github/instructions/` 配下の手順書を参照して、実装を進める。

## ドキュメント

仕様の Single Source of Truth は [`docs/`](./docs/) です（整備中）。

### .github/ — AI 駆動開発の設定

- `.github/copilot-instructions.md`: Copilot 用ルール設定（AI 自動読み込み）
- `.github/instructions/`: タスク別手順書（AI 向けが中心・人間も必要時参照）
- `.github/agents/`: AI エージェント定義
- `.github/prompts/`: 再利用可能プロンプト（`/scaffold` 等）
- `.github/skills/`: AI 専門知識モジュール
- `.github/hooks/`: Copilot 安全フック設定（危険操作の抑止など）

## クイックスタート

> **前提条件**: Python 3.12 以上・SQL Server が起動済みであること。
> 環境変数は `.env.example` をコピーして `.env` を作成し、接続情報を設定してください。

```bash
python -m venv .venv              # 仮想環境作成（初回のみ）
.venv\Scripts\activate            # 仮想環境有効化（Windows）
pip install -e ".[dev]"           # 依存パッケージをインストール（初回のみ）
uvicorn app.main:app --reload     # 開発サーバー起動 (port 8000)
```

起動後、ブラウザで <http://localhost:8000/docs> を開いてください（Swagger UI）。

フロントエンド開発サーバーは `frontend/` ディレクトリで `npm run dev` を実行してください（port 5173）。

> 一括起動スクリプト: `scripts/start-dev.bat`（バックエンド＋フロントエンドを同時起動）

## プロジェクト構成

```text
task-manager/
├── .github/              # Copilot instructions・AI 駆動開発設定
├── app/
│   ├── common/           # 共通ユーティリティ（bulk_update, pagination, email 等）
│   ├── core/             # 共通基盤（auth, result, clock, config, middleware, i18n）
│   └── main.py           # FastAPI アプリケーションエントリーポイント
├── frontend/             # React フロントエンド（Vite + MUI）
├── tests/                # テスト
├── docs/                 # 仕様・設計書（整備中）
├── scripts/              # 開発補助スクリプト（start-dev.bat 等）
└── pyproject.toml        # プロジェクト設定・依存定義
```

## コントリビューション

本プロジェクトへの参加方法は [`CONTRIBUTING.md`](./CONTRIBUTING.md) を参照してください。

## ライセンス

Private
