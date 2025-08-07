// API响应基础结构
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页请求参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应数据
export interface PaginationResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

// 扩展的错误对象类型
export interface ApiError extends Error {
  apiResponse?: ApiResponse;
  businessError?: boolean;
}


