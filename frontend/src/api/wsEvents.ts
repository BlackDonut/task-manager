/**
 * WebSocket 通知イベント型（Phase 15-3 / ADR-0004）。
 *
 * バックエンド: ``app/features/notifications/ws/events.py::WebSocketEvent``
 *
 * サーバー側を SSOT とする。本ファイルは TS 側の写経であり、
 * 追加時は両方を同時更新すること（将来 OpenAPI 連携で自動化を検討）。
 */
export const WsEvent = {
  // --- 通知系 ---
  NotificationCreated: 'notification:created',
  NotificationRead: 'notification:read',
  NotificationReadAll: 'notification:read_all',
  UnreadCountChanged: 'notification:unread_count_changed',

  // --- タスク系 ---
  TaskCreated: 'task:created',
  TaskUpdated: 'task:updated',
  TaskStatusChanged: 'task:status_changed',
  TaskAssigned: 'task:assigned',
  TaskCommentAdded: 'task:comment_added',

  // --- 申請系 ---
  ApplicationStatusChanged: 'application:status_changed',
  ApplicationSubmitted: 'application:submitted',

  // --- 承認系 ---
  ApprovalRequested: 'approval:requested',
  ApprovalDecided: 'approval:decided',

  // --- 期日変更系 ---
  DateChangeRequested: 'date_change:requested',
  DateChangeDecided: 'date_change:decided',

  // --- 接続系（クライアント→サーバー） ---
  Ping: 'ping',
  Pong: 'pong',
} as const;

export type WsEventName = (typeof WsEvent)[keyof typeof WsEvent];

/** WebSocket メッセージの共通エンベロープ。 */
export interface WsMessage<TData = unknown> {
  event: WsEventName | string; // 未知イベントも許容（前方互換性）
  data: TData;
}
