"""i18n（多言語対応）インフラ。

仕様ソース: ``docs/requirements/non-functional-requirements.md`` NFR-008
対応言語: ja / en / zh-CN / vi

ロケール判定優先順:
1. ``User.locale``（DB 保存値）
2. ``Accept-Language`` ヘッダー
3. ``ja``（デフォルト）

メッセージキーは定数化し、``AppError.message`` にキーを入れて
Router 層でローカライズする。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

DEFAULT_LOCALE = "ja"
SUPPORTED_LOCALES = ("ja", "en", "zh-CN", "vi")

# メッセージリソースの配置先
_RESOURCE_DIR = Path(__file__).parent / "i18n_resources"


class I18n:
    """多言語メッセージ解決。

    シングルトン的に使い、ロケールに応じたメッセージを返す。
    存在しないキーは元のキー文字列をそのまま返す（翻訳漏れ検知用）。
    """

    _cache: ClassVar[dict[str, dict[str, str]]] = {}

    @classmethod
    def load_all(cls) -> None:
        """全ロケールのリソースファイルを読み込む。起動時に 1 回呼ぶ。"""
        for locale in SUPPORTED_LOCALES:
            path = _RESOURCE_DIR / f"{locale}.json"
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    cls._cache[locale] = json.load(f)
            else:
                cls._cache[locale] = {}

    @classmethod
    def t(cls, key: str, locale: str = DEFAULT_LOCALE, **kwargs: object) -> str:
        """メッセージキーをローカライズ済み文字列に変換する。

        ``kwargs`` でプレースホルダを置換: ``{count}`` → ``kwargs["count"]``。
        """
        if not cls._cache:
            cls.load_all()
        messages = cls._cache.get(locale, cls._cache.get(DEFAULT_LOCALE, {}))
        template = messages.get(key, key)
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, IndexError):
                return template
        return template

    @classmethod
    def resolve_locale(
        cls,
        *,
        user_locale: str | None = None,
        accept_language: str | None = None,
    ) -> str:
        """ロケール判定（優先順: user_locale → Accept-Language → デフォルト）。"""
        if user_locale and user_locale in SUPPORTED_LOCALES:
            return user_locale
        if accept_language:
            for part in accept_language.split(","):
                lang = part.strip().split(";")[0].strip()
                if lang in SUPPORTED_LOCALES:
                    return lang
                # en-US → en
                short = lang.split("-")[0]
                if short in SUPPORTED_LOCALES:
                    return short
        return DEFAULT_LOCALE
