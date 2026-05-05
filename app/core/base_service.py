"""BaseService — 全 Service の基底クラス。

仕様ソース: ``docs/03_detail-design/01_common/common-backend.md`` §5.10

使用規約:
- 全 Service は ``BaseService`` を継承する
- 例外を Service 外に伝播しない（``Result[T]`` で返す。L2）
- 時刻は ``self._clock.now()`` で取得する（``datetime.now()`` 直接呼び出し禁止。L2）
"""

from __future__ import annotations

from app.common.logger import get_logger
from app.core.clock import Clock


class BaseService:
    """全 Service の基底クラス。"""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        # service 名をログに紐付け、どの Service の呼び出しかを可視化する
        self._log = get_logger(service=self.__class__.__name__)
