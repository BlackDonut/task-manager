"""LDAP アダプター（Active Directory アカウント有効性確認）。

仕様ソース: ``docs/03_detail-design/01_common/auth-design.md`` §11.5

# TODO(security): LDAP 接続のTLS検証・バインドDN権限の最小化
# - requires review before check-in
# - 脅威モデル: docs/02_basic-design/01_common/basic-design.md §LDAP 経路

役割:
- IIS Windows 認証成功後のアカウント有効性確認（無効化・ロック・退職済みの検出）
- パスワード認証は IIS が担うため本アダプターでは行わない

依存: ``python-ldap`` パッケージ（pyproject.toml に追加要）。未インストール時は
``LdapUnavailableAdapter``（常に True を返す）にフォールバックする。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


class LdapAdapter(ABC):
    """LDAP 操作の抽象基底クラス。テスト時のモック差し替え用。"""

    @abstractmethod
    def verify_account(self, login_id: str) -> bool:
        """login_id のアカウントが Active Directory 上で有効かを確認する。"""
        ...


class ActiveDirectoryAdapter(LdapAdapter):
    """Active Directory への LDAP 接続でアカウント有効性を確認する。

    # TODO(security): TLS 証明書検証の有効化 - requires review before check-in
    """

    def __init__(
        self,
        *,
        ldap_url: str,
        base_dn: str,
        bind_dn: str,
        bind_password: str,
        search_filter: str = "(sAMAccountName={login_id})",
    ) -> None:
        self._ldap_url = ldap_url
        self._base_dn = base_dn
        self._bind_dn = bind_dn
        self._bind_password = bind_password
        self._search_filter_template = search_filter

    def verify_account(self, login_id: str) -> bool:
        """Active Directory でアカウントが有効かを確認する。

        ユーザーアカウント制御 (UAC) フラグの ACCOUNTDISABLE (0x0002) を
        チェックし、無効化されたアカウントを拒否する。
        """
        try:
            import ldap  # type: ignore[import-not-found]
        except ImportError:
            logger.error("ldap.import_error", hint="python-ldap パッケージが必要です")
            return False

        conn = None
        try:
            conn = ldap.initialize(self._ldap_url)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            conn.simple_bind_s(self._bind_dn, self._bind_password)

            search_filter = self._search_filter_template.format(login_id=login_id)
            result = conn.search_s(
                self._base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ["userAccountControl"],
            )

            if not result:
                logger.info("ldap.account_not_found", login_id_length=len(login_id))
                return False

            _dn, attrs = result[0]
            uac_values = attrs.get("userAccountControl", [])
            if not uac_values:
                return True

            uac = int(uac_values[0])
            # UAC ビット 0x0002 = ACCOUNTDISABLE
            is_disabled = bool(uac & 0x0002)
            if is_disabled:
                logger.info("ldap.account_disabled", login_id_length=len(login_id))
                return False

            return True

        except Exception:
            logger.exception("ldap.verify_error")
            # フェイルオープン禁止: LDAP エラー時は認証を拒否する
            return False
        finally:
            if conn is not None:
                try:
                    conn.unbind_s()
                except Exception:  # noqa: S110 – cleanup in finally; unbind failure must not mask auth result
                    pass


class LdapUnavailableAdapter(LdapAdapter):
    """LDAP が無効化されている場合のフォールバック（常に有効を返す）。

    ``settings.ldap_enabled = False`` 時に使用する。
    開発環境・テスト環境向け。
    """

    def verify_account(self, login_id: str) -> bool:
        return True


def create_ldap_adapter(
    *,
    enabled: bool,
    ldap_url: str = "",
    base_dn: str = "",
    bind_dn: str = "",
    bind_password: str = "",
    search_filter: str = "(sAMAccountName={login_id})",
) -> LdapAdapter:
    """設定に基づいて適切な LDAP アダプターを生成する。"""
    if not enabled:
        return LdapUnavailableAdapter()

    return ActiveDirectoryAdapter(
        ldap_url=ldap_url,
        base_dn=base_dn,
        bind_dn=bind_dn,
        bind_password=bind_password,
        search_filter=search_filter,
    )
