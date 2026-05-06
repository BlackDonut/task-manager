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
export type TicketTracker = 'bug' | 'feature' | 'support' | 'task'

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
