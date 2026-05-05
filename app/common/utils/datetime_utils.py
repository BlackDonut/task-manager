"""日付・時刻ユーティリティ（変換・判定・フォーマットのみ）。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.2

- 現在日時の取得は ``app.core.clock.Clock`` 経由（L2: ``datetime.now()`` 直接禁止）
- 本モジュールは副作用なしの純粋関数のみ提供
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, timezone

_JST = timezone(timedelta(hours=9))


def to_jst(utc_dt: datetime) -> datetime:
    """UTC → JST（+09:00）変換。naive datetime は UTC とみなす。"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    return utc_dt.astimezone(_JST)


def to_utc(local_dt: datetime) -> datetime:
    """ローカル時刻 → UTC 変換。tz-aware 必須。"""
    if local_dt.tzinfo is None:
        raise ValueError("to_utc requires a timezone-aware datetime")
    return local_dt.astimezone(UTC)


def format_date(dt: datetime | date, fmt: str = "%Y/%m/%d") -> str:
    """日付フォーマット。"""
    return dt.strftime(fmt)


def format_datetime(dt: datetime, fmt: str = "%Y/%m/%d %H:%M") -> str:
    """日時フォーマット。"""
    return dt.strftime(fmt)


def business_days_between(start: date, end: date) -> int:
    """営業日数計算（土日除外。祝日は考慮しない）。

    ``start > end`` の場合は負値を返す（対称性）。1000 日を超える大きな差分では
    計算が線形に増えるため呼び出し側で件数を制限すること。
    """
    if start > end:
        return -business_days_between(end, start)
    count = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # 月〜金
            count += 1
        current += timedelta(days=1)
    return count


def is_past(dt: date, reference: date) -> bool:
    """``dt`` が ``reference`` より過去か判定する。"""
    return dt < reference


def days_until(target: date, reference: date) -> int:
    """``reference`` から ``target`` までの日数（負値 = 過去）。"""
    return (target - reference).days


def start_of_day(dt: datetime) -> datetime:
    """当日 00:00:00 UTC。"""
    return datetime.combine(dt.date(), time.min, tzinfo=UTC)


def end_of_day(dt: datetime) -> datetime:
    """当日 23:59:59.999999 UTC。"""
    return datetime.combine(dt.date(), time.max, tzinfo=UTC)
