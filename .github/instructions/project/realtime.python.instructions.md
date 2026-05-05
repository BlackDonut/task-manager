---
description: "WebSocket の実装パターン。リアルタイム通信・認可チェック・再接続処理・イベント設計を定義する。"
applyTo: "{**/*_websocket.py,**/realtime/**/*.py,**/ws/**/*.py}"
---

# Realtime / WebSocket Standards

## L2 ルール

- WebSocket イベント送信時に認可チェックを省略する場合は警告
- WebSocket ハンドラでビジネスロジックを実装する場合は警告（Service 層に委譲すること）

## 実装パターン

### WebSocket 基本構造（FastAPI）

```python
from fastapi import WebSocket, WebSocketDisconnect, Query

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, org_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(org_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, org_id: str) -> None:
        self.active_connections.get(org_id, []).remove(websocket)

    async def broadcast_to_org(self, org_id: str, event: str, data: dict) -> None:
        for connection in self.active_connections.get(org_id, []):
            await connection.send_json({"event": event, "data": data})

manager = ConnectionManager()

@router.websocket("/ws/events")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await auth_service.validate(token)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.organization_id)
    try:
        while True:
            data = await websocket.receive_text()
            # イベント処理
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.organization_id)
```

### イベント命名規則

```
<entity>:<action>
task:updated
task:created
application:updated
chat:message
```

### セキュリティ

- 接続時に必ず認証トークンを検証
- 組織スコープでルーム分離（他組織のイベントを受信させない）
- センシティブデータ（PII）をイベントペイロードに含めない

### 論理削除ユーザーへのブロードキャスト禁止（L2）

`broadcast_to_org()` は **アクティブな接続** を全件に送信するが、
接続確立後にユーザーが論理削除（`delete_flg = 1`）される場合がある。

**ブロードキャスト呼び出し側（Service 層）でフィルタリングすること**：

```python
class TaskService:
    async def notify_task_updated(self, task: Task) -> None:
        # Service 層でユーザーの有効状態を確認してからブロードキャスト
        # NOTE: broadcast_to_org() は delete_flg チェックをしない。
        # 論理削除ユーザーへの送信を防ぐため、接続時の認証に加えて
        # 通知送信前に Repository で is_active を再確認すること。
        user_result = await self._user_repo.find_active_by_org(task.organization_id)
        if user_result.is_err():
            return
        # 有効ユーザーが存在する組織のみに通知
        await self._manager.broadcast_to_org(
            task.organization_id, "task:updated", task.to_dict()
        )
```

> **補足**: `ConnectionManager` 自体に `delete_flg` フィルタを持たせると
> WebSocket 接続ハンドラにビジネスロジックが混入するため（L2 違反）、
> フィルタは必ず呼び出し元の Service 層に実装すること。

## 参照
