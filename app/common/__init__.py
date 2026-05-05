"""ビジネス共通ユーティリティ。

- 配置方針: 2 機能以上で共有するユーティリティ・変換関数
- 依存方向: ``features/`` → ``common/`` のみ、``common/`` → ``core/`` は OK
  （``common/`` → ``features/*`` は禁止）
- 詳細: ``.github/instructions/project-structure.instructions.md``
"""
