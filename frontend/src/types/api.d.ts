/** 统一 API 响应结构 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  ts: number;
}

/** 分页元数据结构 */
export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** 分页响应结构 */
export interface PaginatedData<T> {
  list: T[];
  pagination: PaginationMeta;
}
