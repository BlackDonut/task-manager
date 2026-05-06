/**
 * API リクエスト/レスポンス型定義（SSOT）。
 * バックエンドの Pydantic スキーマと対応する。
 *
 * 仕様ソース:
 *   - app/features/tickets/list/schemas.py
 *   - app/features/projects/list/schemas.py
 *   - app/features/products/list/schemas.py
 */

// ---- 定数型 ---------------------------------------------------------------

export type TicketStatus = 'new' | 'in_progress' | 'resolved' | 'closed' | 'rejected'
export type TicketPriority = 'urgent' | 'high' | 'normal' | 'low'
export type TicketTracker = 'bug' | 'feature' | 'support' | 'task' | 'phase'

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
 * ガントチャート用チケット 1 件。
 * 仕様ソース: app/features/tickets/gantt/schemas.py
 */
export interface GanttTicketResponse {
  id: number
  subject: string
  product: ProductResponse
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

// ---- リスクダッシュボード型 ------------------------------------------------

/**
 * リスクダッシュボード サマリーカード集計値。
 * 仕様ソース: app/features/tickets/risk/schemas.py
 */
export interface RiskSummary {
  /** 期限超過チケット数（status が resolved/closed/rejected 以外） */
  overdue_count: number
  /** 期限 3 日以内チケット数（未超過・未完了） */
  at_risk_count: number
  /** 担当者未割当の未完了チケット数 */
  unassigned_count: number
  /** new + in_progress の合計チケット数 */
  in_progress_count: number
}

/** 製品別の進捗・遅延集計。 */
export interface ProductRiskSummary {
  product: ProductResponse
  total_count: number
  avg_progress: number
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
  /** 遅延中 + 期限 3 日以内のチケット（最大 200 件） */
  risk_tickets: RiskTicketResponse[]
}

export interface RiskDashboardQuery {
  project_id?: number | null
}
