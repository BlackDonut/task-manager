/**
 * API リクエスト/レスポンス型定義（SSOT）。
 * バックエンドの Pydantic スキーマと対応する。
 *
 * 仕様ソース:
 *   - app/features/tickets/list/schemas.py
 *   - app/features/projects/list/schemas.py
 *   - app/features/products/list/schemas.py
 *   - app/features/product_releases/list/schemas.py
 */

// ---- 定数型 ---------------------------------------------------------------

export type TicketStatus = 'new' | 'in_progress' | 'resolved' | 'closed' | 'rejected'
export type TicketPriority = 'urgent' | 'high' | 'normal' | 'low'
export type TicketTracker = 'bug' | 'feature' | 'support' | 'task' | 'phase'

// co-change: app/models/product.py RELEASE_TYPE_* 定数
/** 作業サイクル種別 */
export type ReleaseType = 'initial' | 'spec_change' | 'version_upgrade' | 'maintenance'

// co-change: app/models/product.py RELEASE_STATUS_* 定数
/** 作業サイクル進捗 */
export type ReleaseStatus = 'planning' | 'in_progress' | 'completed'

// ---- レスポンス型 -----------------------------------------------------------

export interface AssigneeResponse {
  id: number
  display_name: string
}

export interface ProductResponse {
  id: number
  name: string
}

export interface TicketResponse {
  id: number
  product: ProductResponse
  parent_id: number | null
  /** 作業サイクル ID (product_releases.id)。null=サイクル未分類 */
  release_id: number | null
  tracker: TicketTracker
  status: TicketStatus
  priority: TicketPriority
  subject: string
  assignee: AssigneeResponse | null
  due_date: string | null
  updated_at: string
  done_ratio: number
  /** 階層深度。0=ルート/フェーズ, 1=子, 2=孫, 3=曾孫 */
  depth: number
  /** 先行チケット ID リスト（前後関係） */
  predecessor_ids: number[]
}

export interface TicketListResponse {
  items: TicketResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ---- クエリパラメータ型 -----------------------------------------------------

export interface TicketListQuery {
  project_id?: number | null
  product_id?: number | null
  /** 作業サイクル ID でフィルタ (product_releases.id) */
  release_id?: number | null
  status?: TicketStatus | null
  priority?: TicketPriority | null
  tracker?: TicketTracker | null
  assignee_id?: number | null
  keyword?: string | null
  page?: number
  page_size?: number
}

// ---- プロジェクト型 ---------------------------------------------------------

/** プロジェクト 1 件。仕様ソース: app/features/projects/list/schemas.py */
export interface ProjectItem {
  id: number
  name: string
}

export interface ProjectListResponse {
  items: ProjectItem[]
  total: number
}

// ---- 製品型 ---------------------------------------------------------

/** 製品 1 件。仕様ソース: app/features/products/list/schemas.py */
export interface ProductItem {
  id: number
  project_id: number
  name: string
}

export interface ProductListResponse {
  items: ProductItem[]
  total: number
}

// ---- ガントチャート型 -------------------------------------------------------

/**
 * ガントチャート用製品情報。project_id を含む（プロジェクト横断グループ化に使用）。
 * 仕様ソース: app/features/tickets/gantt/schemas.py GanttProductResponse
 */
export interface GanttProductResponse {
  id: number
  name: string
  /** 所属プロジェクト ID（プロジェクト単位グループ化に使用） */
  project_id: number
}

/**
 * ガントチャート用チケット 1 件。
 * 仕様ソース: app/features/tickets/gantt/schemas.py
 */
export interface GanttTicketResponse {
  id: number
  subject: string
  product: GanttProductResponse
  parent_id: number | null
  status: TicketStatus
  priority: TicketPriority
  tracker: TicketTracker
  done_ratio: number
  /** 開始日 (YYYY-MM-DD)。チケット作成日を使用 */
  start_date: string
  /** 期日 (YYYY-MM-DD)。未設定の場合は null */
  due_date: string | null
  assignee: AssigneeResponse | null
  /** 階層深度。0=ルート/フェーズ, 1=子, 2=孫, 3=曾孫 */
  depth: number
  /** 先行チケット ID リスト（前後関係） */
  predecessor_ids: number[]
}

export interface GanttTicketListResponse {
  items: GanttTicketResponse[]
  /** フィルタ後の総件数（最大 500 件） */
  total: number
}

export interface GanttTicketQuery {
  project_id?: number | null
  product_id?: number | null
  status?: TicketStatus | null
  tracker?: TicketTracker | null
  priority?: TicketPriority | null
  assignee_id?: number | null
}

// ---- チケット作成型 -----------------------------------------------------------

/**
 * チケット作成リクエスト。
 * 仕様ソース: app/features/tickets/create/schemas.py TicketCreateRequest
 */
export interface TicketCreateRequest {
  product_id: number
  /** 作業サイクル ID (product_releases.id)。null=サイクル未分類 */
  release_id?: number | null
  parent_id?: number | null
  tracker: TicketTracker
  /** デフォルト: 'new' */
  status: TicketStatus
  /** デフォルト: 'normal' */
  priority: TicketPriority
  subject: string
  assignee_id?: number | null
  /** YYYY-MM-DD 形式 */
  due_date?: string | null
  done_ratio?: number
  /** 先行チケット ID リスト（Finish-to-Start 依存）。省略時は空配列として扱う。 */
  predecessor_ids?: number[]
}

/**
 * チケット作成レスポンス。
 * 仕様ソース: app/features/tickets/create/schemas.py TicketCreateResponse
 */
export type TicketCreateResponse = TicketResponse

/**
 * チケット更新リクエスト。product_id は変更不可。
 * 仕様ソース: app/features/tickets/update/schemas.py TicketUpdateRequest
 */
export interface TicketUpdateRequest {
  tracker: TicketTracker
  status: TicketStatus
  priority: TicketPriority
  subject: string
  /** 作業サイクル ID (product_releases.id)。null=サイクル未分類 */
  release_id?: number | null
  assignee_id?: number | null
  /** YYYY-MM-DD 形式 */
  due_date?: string | null
  done_ratio?: number
  parent_id?: number | null
  /** 先行チケット ID リスト（Finish-to-Start 依存） */
  predecessor_ids?: number[]
}

/**
 * チケット更新レスポンス。
 * 仕様ソース: app/features/tickets/update/schemas.py TicketUpdateResponse
 */
export type TicketUpdateResponse = TicketResponse

// ---- リスクダッシュボード型 ------------------------------------------------

/**
 * リスクダッシュボード サマリーカード集計値。
 * 仕様ソース: app/features/tickets/risk/schemas.py
 */
export interface RiskSummary {
  /** 期限超過チケット数（status が resolved/closed/rejected 以外） */
  overdue_count: number
  /** 期限 1 週間以内チケット数（未超過・未完了） */
  at_risk_count: number
  /** 担当者未割当の未完了チケット数 */
  unassigned_count: number
  /** new + in_progress の合計チケット数 */
  in_progress_count: number
  /** 未着手（status=new）かつ期限が 1 週間超または期限なしのチケット数 */
  todo_count: number
}

/** 製品別の遅延集計。 */
export interface ProductRiskSummary {
  product: ProductResponse
  total_count: number
  overdue_count: number
}

/** リスク一覧に表示するチケット 1 件。 */
export interface RiskTicketResponse {
  id: number
  subject: string
  product: ProductResponse
  status: TicketStatus
  priority: TicketPriority
  tracker: TicketTracker
  due_date: string | null
  /** 正値 = 超過日数、負値 = 残り日数、0 = 当日。due_date が null の場合は 0 */
  overdue_days: number
  assignee: AssigneeResponse | null
  done_ratio: number
  /** 先行チケット ID リスト（前後関係） */
  predecessor_ids: number[]
}

/** リスクダッシュボード レスポンス全体。 */
export interface RiskDashboardResponse {
  summary: RiskSummary
  product_summaries: ProductRiskSummary[]
  /** 期限超過チケット（due_date < 今日・件数制限なし） */
  overdue_tickets: RiskTicketResponse[]
  /** 期限 1 週間以内チケット（今日 <= due_date <= 7 日後・件数制限なし） */
  at_risk_tickets: RiskTicketResponse[]
  /** 未着手（status=new）かつ期限が 1 週間超または期限なしのチケット（最大 200 件） */
  todo_tickets: RiskTicketResponse[]
}

export interface RiskDashboardQuery {
  project_id?: number | null
}

// ---- 製品作業サイクル型 -----------------------------------------------------

/**
 * 製品作業サイクル 1 件。
 * 仕様ソース: app/features/product_releases/list/schemas.py
 */
export interface ProductReleaseItem {
  id: number
  product_id: number
  name: string
  release_type: ReleaseType
  status: ReleaseStatus
  /** 目標完了日 (YYYY-MM-DD)。未設定の場合は null */
  target_date: string | null
}

export interface ProductReleaseListResponse {
  items: ProductReleaseItem[]
  total: number
}

export interface ProductReleaseCreateRequest {
  product_id: number
  name: string
  release_type: ReleaseType
  status: ReleaseStatus
  /** YYYY-MM-DD 形式または null */
  target_date?: string | null
}

export interface ProductReleaseUpdateRequest {
  name: string
  release_type: ReleaseType
  status: ReleaseStatus
  /** YYYY-MM-DD 形式または null */
  target_date?: string | null
}

// ---- タスクグループ型 -------------------------------------------------------
// co-change: app/features/task_groups/list/schemas.py

/** グループメンバー 1 件のサマリー */
export interface GroupMemberSummary {
  ticket_id: number
  subject: string
  status: string
  product_name: string
  /** ISO 8601 */
  added_at: string
}

/**
 * タスクグループ 1 件。
 * 仕様ソース: app/features/task_groups/list/schemas.py TaskGroupItem
 */
export interface TaskGroupItem {
  id: number
  name: string
  description: string | null
  member_count: number
  members: GroupMemberSummary[]
}

export interface TaskGroupListResponse {
  items: TaskGroupItem[]
  total: number
}

export interface TaskGroupCreateResponse {
  id: number
  name: string
  description: string | null
  members: GroupMemberSummary[]
}

export interface TaskGroupCreateRequest {
  name: string
  description?: string | null
  /** 2 件以上必須 */
  ticket_ids: number[]
}

export interface TaskGroupUpdateRequest {
  name: string
  description?: string | null
}

export interface TaskGroupAddMembersRequest {
  ticket_ids: number[]
}

export interface TaskGroupRemoveMembersRequest {
  ticket_ids: number[]
}

// ---- フェーズ進捗マトリクス型 -----------------------------------------------

/**
 * フェーズセルの状態区分。
 * co-change: app/features/tickets/matrix/schemas.py PhaseState
 */
export type PhaseState =
  | 'completed'   // resolved または closed
  | 'overdue'     // active かつ期限超過
  | 'in_progress' // 進行中（期限内）
  | 'not_started' // 未着手（期限内または期限なし）
  | 'rejected'    // 却下
  | 'none'        // フェーズチケットなし

/** マトリクスのセル 1 件。 */
export interface PhaseCell {
  phase_subject: string
  ticket_id: number | null
  status: string | null
  /** 期日 (YYYY-MM-DD) または null */
  due_date: string | null
  state: PhaseState
}

/** 製品 1 行分のデータ。 */
export interface ProductPhaseRow {
  product: ProductResponse
  /** phases リストと同順のセル一覧 */
  cells: PhaseCell[]
}

/**
 * フェーズ進捗マトリクス レスポンス全体。
 * 仕様ソース: app/features/tickets/matrix/schemas.py PhaseMatrixResponse
 */
export interface PhaseMatrixResponse {
  /** 全製品にわたるフェーズ名の昇順ソート一覧（列定義） */
  phases: string[]
  /** 製品ごとの行。phases と同順のセルを持つ */
  rows: ProductPhaseRow[]
}

export interface PhaseMatrixQuery {
  project_id?: number | null
}
