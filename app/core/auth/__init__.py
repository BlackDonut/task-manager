"""認証・認可基盤。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md``

Phase 1 スコープ:
- ``AuthenticatedUser`` / ``OrganizationScope`` / ``PermissionRef`` の型定義
- ``get_current_user`` / ``permission_required`` の Depends スケルトン
- RBAC / ABAC の判定ロジック（ユニットテスト可能な純粋関数として切り出す）

スコープ外（Phase 1 後半で別途実装）:
- IIS ヘッダー ``x-iis-windowsauth-user`` からの実ユーザー解決
- LDAP でのアカウント有効性確認
- Redis セッションの read/write

これらは ``# TODO(security):`` で明示し、本番投入前のセキュリティレビューを必須化する。
"""
