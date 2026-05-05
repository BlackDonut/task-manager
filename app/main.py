"""FastAPI アプリケーションのエントリポイント。

仕様ソース:
- ``docs/03_detail-design/01_common/backend-design.md``
- ``.github/instructions/project-structure.instructions.md`` §モジュール登録

各機能ルーターは ``app/features/{domain}/{subfeature}/router.py`` を `include_router` で
登録する。新規ドメイン/サブ機能追加時は ``folder-structure.md`` の規約に従って配置した上で、
本ファイル末尾の router 登録ブロックに追加すること。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.logger import configure_logging
from app.core.config import get_settings
from app.core.middleware.error_handler import register_exception_handlers
from app.core.middleware.logging_middleware import AccessLoggingMiddleware
from app.core.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    """FastAPI アプリケーションを生成する。

    アプリケーションファクトリパターンを採用。テストで複数インスタンス生成可能にする。
    """
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )

    # --- CORS（開発時のみ。本番では静的ファイル同一オリジン配信） ---
    if settings.app_env != "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # --- 開発用認証バイパスミドルウェア ---
    # # TODO(security): 本番環境では絶対に有効化しない - requires review before check-in
    if settings.app_env == "development":
        from app.core.middleware.dev_auth import DevAuthMiddleware

        app.add_middleware(DevAuthMiddleware)
    elif settings.app_env in ("staging", "production"):
        # --- 本番用: IIS Windows 認証 + LDAP + Redis セッション ---
        import redis.asyncio as aioredis

        from app.core.auth.iis_auth import IISAuthMiddleware
        from app.core.auth.ldap_adapter import create_ldap_adapter
        from app.core.auth.session import SessionMiddleware

        redis_client = aioredis.from_url(
            settings.redis_url,
            password=settings.redis_password.get_secret_value() if settings.redis_password else None,
        )
        # WebSocket エンドポイントが BaseHTTPMiddleware をバイパスするため、
        # redis_client を app.state に格納してセッション検証に使用する。
        # （auth-design.md §11.2 / WebSocket 認証設計）
        app.state.redis_client = redis_client
        ldap_adapter = create_ldap_adapter(
            enabled=settings.ldap_enabled,
            ldap_url=settings.ldap_url,
            base_dn=settings.ldap_base_dn,
            bind_dn=settings.ldap_bind_dn,
            bind_password=(settings.ldap_bind_password.get_secret_value() if settings.ldap_bind_password else ""),
            search_filter=settings.ldap_user_search_filter,
        )
        app.add_middleware(
            IISAuthMiddleware,
            redis_client=redis_client,
            ldap_adapter=ldap_adapter,
            session_max_age=settings.session_max_age_seconds,
        )
        app.add_middleware(
            SessionMiddleware,
            redis_client=redis_client,
            max_age=settings.session_max_age_seconds,
            is_secure=settings.session_cookie_secure,
        )

    # --- ミドルウェア登録（逆順で適用される。外側=最初に書く） ---
    # RequestIdMiddleware を最外に置いてログに request_id を常に乗せる
    app.add_middleware(AccessLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # --- 例外ハンドラ ---
    register_exception_handlers(app)

    # --- ヘルスチェック（認可不要。運用監視用） ---
    @app.get("/healthz", tags=["system"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # --- 機能ルーター ---
    # 認証（login / logout）
    from app.features.auth.login.router import router as auth_router

    app.include_router(auth_router)

    # Phase 2 縦割りスライス: マスタデータ
    from app.features.admin.users.router import router as users_router
    from app.features.applications.applications.router import router as applications_router
    from app.features.applications.certificates.router import router as certificates_router
    from app.features.applications.documents.router import router as documents_router
    from app.features.applications.product_countries.router import (
        router as product_countries_router,
    )
    from app.features.applications.products.router import router as products_router
    from app.features.applications.projects.router import router as projects_router
    from app.features.applications.submission_companies.router import (
        router as submission_companies_router,
    )
    from app.features.master.countries.router import router as countries_router
    from app.features.tasks.tasks.router import router as tasks_router

    app.include_router(countries_router)
    app.include_router(projects_router)
    app.include_router(products_router)
    app.include_router(tasks_router)

    # SCR040: 申請・タスク関係管理（ADR-0006）
    # NOTE: applications_router の GET /{application_id} より先に登録しないと
    #       GET /api/v1/applications/dependencies が /{application_id} にマッチしてしまう。
    from app.features.applications.application_dependencies.router import (
        router as app_dependencies_router,
    )

    app.include_router(app_dependencies_router)

    app.include_router(applications_router)
    app.include_router(users_router)
    # Phase 3: 申請管理ワークフロー
    app.include_router(product_countries_router)
    app.include_router(submission_companies_router)
    app.include_router(documents_router)
    app.include_router(certificates_router)

    # Phase 5: 承認ワークフロー
    from app.features.applications.shipping_gate.router import router as shipping_gate_router

    app.include_router(shipping_gate_router)

    # Phase 4: タスクガバナンス
    from app.features.tasks.backlog.router import router as backlog_router
    from app.features.tasks.comments.router import router as comments_router
    from app.features.tasks.messages.router import router as task_messages_router
    from app.features.tasks.reg_watch_urls.router import router as reg_watch_urls_router
    from app.features.tasks.task_dependencies.router import router as task_dependencies_router
    from app.features.tasks.templates.router import router as templates_router

    app.include_router(task_dependencies_router)
    app.include_router(comments_router)
    app.include_router(task_messages_router)
    app.include_router(backlog_router)
    app.include_router(templates_router)
    app.include_router(reg_watch_urls_router)

    # Phase 5R: 期日変更承認ワークフロー
    from app.features.tasks.date_change.router import router as date_change_router

    app.include_router(date_change_router)

    # Phase 6: 通知
    from app.features.notifications.inbox.router import router as notification_router
    from app.features.notifications.preferences.router import router as preference_router
    from app.features.notifications.watcher.router import router as watcher_router

    app.include_router(notification_router)
    app.include_router(watcher_router)
    app.include_router(preference_router)

    # Phase 6R: エスカレーションルール CRUD
    from app.features.notifications.escalations.router import router as escalation_router

    app.include_router(escalation_router)

    # Phase 6R: WebSocket リアルタイム通知
    from app.features.notifications.ws.router import router as ws_router

    app.include_router(ws_router)

    # Phase 6R: 承認権限委譲
    from app.features.auth.delegations.router import router as delegation_router

    app.include_router(delegation_router)

    # Dashboard（SCR001）
    from app.features.dashboard.overview.router import router as dashboard_router

    app.include_router(dashboard_router)

    # Phase 8: 監査ログ検索・エクスポート（SCR032）
    from app.features.admin.audit_log.router import router as audit_log_router

    app.include_router(audit_log_router)

    # Phase 8: 法規制変更一括再評価（FR-040）
    from app.features.applications.regulation_re_evaluation.router import (
        router as regulation_router,
    )

    app.include_router(regulation_router)

    # マスタ管理: ロール・部門（B-2-1 / B-2-2）
    from app.features.master.departments.router import router as departments_router
    from app.features.master.roles.router import router as roles_router

    app.include_router(roles_router)
    app.include_router(departments_router)

    # SCR014: 製品構成部品管理
    from app.features.applications.product_components.router import (
        router as product_components_router,
    )

    app.include_router(product_components_router)

    # SCR011: 申請提出バッチ管理（ADR-0007）
    from app.features.applications.submission_batches.router import (
        router as submission_batches_router,
    )

    app.include_router(submission_batches_router)

    # SCR004D: 手順書バージョン管理（FR-041〜FR-043）
    # NOTE: /{application_id} パスと衝突しないよう applications_router より先に登録すること
    from app.features.applications.procedures.router import router as procedures_router

    app.include_router(procedures_router)

    # SCR041: 再申請管理（F-213〜F-216）
    from app.features.applications.reapplication.router import router as reapplication_router

    app.include_router(reapplication_router)

    # SCR036: システムお知らせ管理（保守対応・障害告知バナー）
    from app.features.admin.system_announcements.router import (
        router as system_announcements_router,
    )

    app.include_router(system_announcements_router)

    # SCR015: 書類テンプレートマスタ（F-220〜F-224）
    from app.features.applications.document_templates.router import router as document_templates_router

    app.include_router(document_templates_router)

    return app


app = create_app()
