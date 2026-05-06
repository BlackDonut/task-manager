/**
 * API 呼び出し関数（ドメイン別オブジェクト）。
 *
 * 仕様ソース:
 *   - app/features/tickets/list/router.py
 *   - app/features/projects/list/router.py
 */
import apiClient from '../client'
import type {
  GanttTicketListResponse,
  GanttTicketQuery,
  ProductListResponse,
  ProjectListResponse,
  TicketListQuery,
  TicketListResponse,
} from './types'

/** チケット管理 API */
export const ticketsApi = {
  /** チケット一覧取得（フィルタ・ページネーション付き） */
  getList: (query?: TicketListQuery) =>
    apiClient.get<TicketListResponse>('/tickets', { params: query }),

  /** ガントチャート用チケット一覧取得（フィルタ付き・最大 500 件・ページネーションなし） */
  getGanttList: (query?: GanttTicketQuery) =>
    apiClient.get<GanttTicketListResponse>('/tickets/gantt', { params: query }),
}

/** プロジェクト API */
export const projectsApi = {
  /** チケットフィルタ用プロジェクト一覧取得 */
  getList: () => apiClient.get<ProjectListResponse>('/projects'),
}

/** 製品 API */
export const productsApi = {
  /** 製品一覧取得。project_id を指定するとそのプロジェクト配下のみ返す */
  getList: (project_id?: number | null) =>
    apiClient.get<ProductListResponse>('/products', { params: project_id != null ? { project_id } : undefined }),
}
