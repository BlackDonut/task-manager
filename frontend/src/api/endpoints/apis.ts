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
  PhaseMatrixQuery,
  PhaseMatrixResponse,
  ProductListResponse,
  ProductReleaseCreateRequest,
  ProductReleaseItem,
  ProductReleaseListResponse,
  ProductReleaseUpdateRequest,
  ProjectListResponse,
  RiskDashboardQuery,
  RiskDashboardResponse,
  TaskGroupAddMembersRequest,
  TaskGroupCreateRequest,
  TaskGroupCreateResponse,
  TaskGroupItem,
  TaskGroupListResponse,
  TaskGroupRemoveMembersRequest,
  TaskGroupUpdateRequest,
  TicketCreateRequest,
  TicketCreateResponse,
  TicketListQuery,
  TicketListResponse,
  TicketUpdateRequest,
  TicketUpdateResponse,
} from './types'

/** チケット管理 API */
export const ticketsApi = {
  /** チケット一覧取得（フィルタ・ページネーション付き） */
  getList: (query?: TicketListQuery) =>
    apiClient.get<TicketListResponse>('/tickets', { params: query }),

  /** ガントチャート用チケット一覧取得（フィルタ付き・最大 500 件・ページネーションなし） */
  getGanttList: (query?: GanttTicketQuery) =>
    apiClient.get<GanttTicketListResponse>('/tickets/gantt', { params: query }),

  /** リスクダッシュボード取得（遅延・期限直前・未割当の集計 + チケット一覧） */
  getRiskSummary: (query?: RiskDashboardQuery) =>
    apiClient.get<RiskDashboardResponse>('/tickets/risk-summary', { params: query }),

  /** 新規チケットを作成する。201 Created を返す。 */
  create: (data: TicketCreateRequest) =>
    apiClient.post<TicketCreateResponse>('/tickets', data),

  /** 既存チケットを更新する。200 OK を返す。 */
  update: (ticketId: number, data: TicketUpdateRequest) =>
    apiClient.patch<TicketUpdateResponse>(`/tickets/${ticketId}`, data),

  /** フェーズ進捗マトリクス取得（製品×フェーズのクロス集計。SCR005 専用） */
  getPhaseMatrix: (query?: PhaseMatrixQuery) =>
    apiClient.get<PhaseMatrixResponse>('/tickets/phase-matrix', { params: query }),
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

/** 製品作業サイクル API（初回リリース / 仕様変更 / バージョンアップ等の管理） */
export const productReleasesApi = {
  /** 製品作業サイクル一覧取得。product_id を指定するとその製品のサイクルのみ返す */
  getList: (product_id?: number | null) =>
    apiClient.get<ProductReleaseListResponse>('/product-releases', {
      params: product_id != null ? { product_id } : undefined,
    }),

  /** 製品作業サイクルを新規作成する。201 Created を返す。 */
  create: (data: ProductReleaseCreateRequest) =>
    apiClient.post<ProductReleaseItem>('/product-releases', data),

  /** 既存の作業サイクルを更新する。200 OK を返す。 */
  update: (releaseId: number, data: ProductReleaseUpdateRequest) =>
    apiClient.patch<ProductReleaseItem>(`/product-releases/${releaseId}`, data),
}

/** タスクグループ API（クロス製品・クロスプロジェクトのチケット束ね・自動完了） */
export const taskGroupsApi = {
  /** タスクグループ一覧取得 */
  getList: () =>
    apiClient.get<TaskGroupListResponse>('/task-groups'),

  /** 指定チケットが属するグループ一覧取得 */
  getByTicket: (ticketId: number) =>
    apiClient.get<TaskGroupListResponse>(`/task-groups/by-ticket/${ticketId}`),

  /** タスクグループ新規作成 */
  create: (data: TaskGroupCreateRequest) =>
    apiClient.post<TaskGroupCreateResponse>('/task-groups', data),

  /** グループ名・説明更新 */
  update: (groupId: number, data: TaskGroupUpdateRequest) =>
    apiClient.patch<TaskGroupItem>(`/task-groups/${groupId}`, data),

  /** グループにチケットを追加 */
  addMembers: (groupId: number, data: TaskGroupAddMembersRequest) =>
    apiClient.post<TaskGroupItem>(`/task-groups/${groupId}/members`, data),

  /** グループからチケットを削除（単票外し・グループ解散） */
  removeMembers: (groupId: number, data: TaskGroupRemoveMembersRequest) =>
    apiClient.delete<TaskGroupItem>(`/task-groups/${groupId}/members`, { data }),

  /** グループ論理削除 */
  delete: (groupId: number) =>
    apiClient.delete(`/task-groups/${groupId}`),
}
