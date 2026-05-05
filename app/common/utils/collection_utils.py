"""コレクション操作ユーティリティ（純粋関数）。

仕様ソース: ``docs/03_detail-design/01_common/common-utils.md`` §5.11.5
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")


def chunk[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """シーケンスを指定サイズで分割する。"""
    if size < 1:
        raise ValueError("size must be >= 1")
    for i in range(0, len(items), size):
        yield items[i : i + size]


def unique_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> list[T]:
    """キー関数による重複除去（順序維持）。"""
    seen: set[K] = set()
    result: list[T] = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def group_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """キー関数によるグルーピング。"""
    result: dict[K, list[T]] = {}
    for item in items:
        result.setdefault(key(item), []).append(item)
    return result


def flatten[T](nested: Iterable[Iterable[T]]) -> list[T]:
    """ネストされたイテラブルの平坦化（1 段のみ）。"""
    return [item for sub in nested for item in sub]


def first_or_none[T](items: Iterable[T], predicate: Callable[[T], bool]) -> T | None:
    """条件に合致する最初の要素を返す。見つからなければ None。"""
    return next((item for item in items if predicate(item)), None)


def index_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> dict[K, T]:
    """キーで辞書化（重複時は後勝ち）。"""
    return {key(item): item for item in items}
